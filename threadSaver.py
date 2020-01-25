#Necessary imports
import requests
import json
import sqlite3
import re
import time
import os

#Disable warnings thrown by requests (I disable ssl verification when getting images because at the time of posting, 4chan's SSL is expired for the image hosting domain)
requests.packages.urllib3.disable_warnings() 

#Connect to database
db = sqlite3.connect("chanStore.sqlite")
c = db.cursor()

#Create main threads table if it's not already there
c.execute("""
CREATE TABLE IF NOT EXISTS Threads (
    ID INT NOT NULL, 
    Board Varchar(10) NOT NULL,
    Title Varchar(100),
    Comment Varchar(2000), 
    PostTime Varchar(30) NOT NULL, 
    Replies INT NOT NULL, 
    ImageCount INT NOT NULL,
    UniqueIPs INT NOT NULL, 
    OP Varchar(100) NOT NULL,
    IsArchived BIT NOT NULL,
    PRIMARY KEY(ID,Board)
)""")

#Create posts table if not already there
c.execute("""CREATE TABLE IF NOT EXISTS Posts (
    ID INT NOT NULL,
    ParentID INT NOT NULL,
    Board VARCHAR(10) NOT NULL,
    Comment Varchar(2000),
    PostTime Varchar(30) NOT NULL,
    TimeStamp INT NOT NULL,
    OP Varchar(100) NOT NULL,
    ImgName Varchar(500),
    ImgExt Varchar(5),
    ImgW INT,
    ImgH INT,
    ImgSize INT,
    ImgDeleted BIT,
    PRIMARY KEY (ID,ParentID,Board)
)""")

#Downloads an entire 4chan thread (Can be re-called to update a thread)
#Returns false if the thread was archived or deleted, and true if it's not archived and still active
def saveThread(postUrl):

    #Lift the board and thread number from the URL
    postUrl = postUrl.split('/')
    board = postUrl[3]
    threadno = postUrl[5]

    #Main thread requests
    apiURL = 'http://a.4cdn.org/' + board + '/thread/' + threadno.strip() + '.json'
    page = requests.get(apiURL)
    #Exit if the thread doesn't exist anymore
    if(not page.content):
        c.execute("UPDATE Threads SET IsArchived=1 WHERE ID=%s AND Board='%s'" % (threadno,board))
        return False
        
    #Parse it as JSON
    thread = page.json()
    time.sleep(1)

    #Wrap the board variable in single quotes for SQL
    board = "'" + board + "'"

    #Store the thread's metadata (which is stored in the 1st post in the thread)
    storeThreadData(thread['posts'][0],board)

    #Exit early if a thread has already been downloaded before, and is currently archived
    #This allows new threads that are currently archived through
    c.execute("SELECT ParentID FROM Posts WHERE Board=%s AND ParentID=%s" % (board,threadno))
    if ('archived' in thread['posts'][0]) and c.fetchall():
        c.execute("UPDATE Threads SET IsArchived=1 WHERE ID=%s AND Board=%s" % (threadno,board))
        return False

    #Getting thread name for folder directory
    Title = 'NULL'
    if 'sub' in thread['posts'][0]:
        Title = cleanse(thread['posts'][0]['sub'])

    #Get highest post ID currently stored for the thread. This allows for efficient checking if a post is in the table without blasting it with queries (As post IDs always increment)
    c.execute("""
        SELECT MAX(ID) FROM Posts
        WHERE Board = %s AND ParentID = %s
    """ % (board,threadno))
    #Lift max ID from results
    results = c.fetchall()
    maxID = results[0][0]
    if maxID is None:
        maxID = 0

    #Iterate through posts
    for post in thread['posts']:
        #Lift all data from the post
        ID = post['no']
        PostTime = "'" + post['now'] + "'"
        TimeStamp = post['time']
        OP = "'" + cleanse(post['name']) + "'"
        
        #Optional parameters
        Comment = 'NULL'
        if 'com' in post:
            Comment = "'" + cleanse(post['com']) + "'" 
        ImgDeleted = 'NULL'
        if 'filedeleted' in post:
            ImgDeleted = "1"
        
        #If there's an image attached, get its attributes
        (ImgName,ImgExt,ImgW,ImgH,ImgSize) = ('NULL','NULL','NULL','NULL','NULL')
        if 'filename' in post:
            ImgName = "'" + cleanse(post['filename']) + "'"
            ImgExt = "'" + post['ext'] + "'"
            ImgW = str(post['w'])
            ImgH = str(post['h'])
            ImgSize = str(post['fsize'])

        #If the post ID is higher than the current thread max ID, then it's not in the table yet and can be inserted
        if(ID > maxID):
            c.execute("INSERT INTO Posts VALUES(%i,%i,%s,%s,%s,%i,%s,%s,%s,%s,%s,%s,%s)" % (ID,int(threadno),board,Comment,PostTime,TimeStamp,OP,ImgName,ImgExt,ImgW,ImgH,ImgSize,ImgDeleted))
            
            #If the image exists on 4chan, proceed to download it
            if (ImgName != 'NULL') and (ImgDeleted != "1"):
                imageURL = 'https://is2.4chan.org/' + board.replace("'",'') + '/' + str(post['tim']) + post['ext']

                #Passing target URL, board, thread number, post ID, image extention, image filename, and thread title to the image saving function
                saveImage(imageURL,board,threadno,ID,post['ext'],cleanse(post['filename']),Title)

    #Return false if it's archived, true otherwise
    if ('archived' in thread['posts'][0]):
        return False
    else:
        return True


#Handles storing the metadata of the thread
def storeThreadData(rootPost,Board):
    #Lift all relevant data out of the root post
    ID = rootPost['no']
    PostTime = "'" + rootPost['now'] + "'"
    Replies = rootPost['replies']
    ImageCount = rootPost['images'] + 1
    OP = "'" + cleanse(rootPost['name']) + "'"

    #Optional parameters
    Title = 'NULL'
    if 'sub' in rootPost:
        Title = "'" + cleanse(rootPost['sub']) + "'"
    Comment = 'NULL'
    if 'com' in rootPost:
        Comment = "'" + cleanse(rootPost['com']) + "'"
    UniqueIPs = -1
    if 'unique_ips' in rootPost:
        UniqueIPs = rootPost['unique_ips']
    Archived = 0
    if 'archived' in rootPost:
        Archived = 1

    #Query to see if the thread is already in the DB, to determine if INSERT or UPDATE
    c.execute("SELECT ID FROM Threads WHERE ID=%i AND Board=%s" % (ID,Board))
    if(not c.fetchall()):
        c.execute("INSERT INTO Threads VALUES (%i,%s,%s,%s,%s,%i,%i,%i,%s,%i)" % (ID,Board,Title,Comment,PostTime,Replies,ImageCount,UniqueIPs,OP,Archived))
    else:
        #Archived posts don't contain the Unique IPs parameter, and this prevents overwriting if it's attempted to be updated
        if UniqueIPs > 0:
            c.execute("UPDATE Threads SET Replies=%i, ImageCount=%i, UniqueIPs=%i, IsArchived=%i WHERE ID=%i AND Board=%s" % (Replies,ImageCount,UniqueIPs,Archived,ID,Board))
        else:
            c.execute("UPDATE Threads SET Replies=%i, ImageCount=%i, IsArchived=%i WHERE ID=%i AND Board=%s" % (Replies,ImageCount,Archived,ID,Board))

#Downloads a target image
def saveImage(url,board,threadID,postID,extention,filename,threadtitle):
    #Piecing together the thread folder name
    if threadtitle == 'NULL':
        threadtitle = ''
    folderName =str(threadID) + cleanFilename(threadtitle)
    directory = 'images/' + board.replace("'",'') + '/' + folderName

    #Peicing together the filename
    filename = str(postID) + cleanFilename(filename) + extention
    filename = directory + '/' + filename

    #Create directories if they don't exist
    if not os.path.exists(directory):
        os.makedirs(directory)
        
    #Downloads and writes 1024 byte blocks from the URL until it recieves an empty block
    #This downloads files without overloading python's memory
    with open(filename, 'wb') as handler:
        data = requests.get(url,stream=True, verify=False) #Disable SSL verification due to their cert being expired rn
        for block in data.iter_content(1024):
            if not block:
                break
            handler.write(block)
 
        print("saved: " + filename.split('/')[3])
        time.sleep(1)

#Cleans strings so they can be neatly passed into the database (4chan comments and stuff contain HTML tags)
def cleanse(string):
    #Removes padding whitespace
    string = string.strip()

    #Strips tags from text, but swap <br> for newline
    string = string.replace("<br>","\n")
    string = re.sub(r'<[^>]*>',"",string)

    #Strips character tags from text, but swap &gt; for meme arrows
    string = string.replace("&gt;",">")
    string = re.sub(r'&[#a-zA-Z0-9]+;',"", string)

    #Remove characters that could break the SQL statement
    string = string.replace("'","").replace("\\","-")

    #Return the result
    return string

#function to make filenames compliant with windows
def cleanFilename(text):
    #Only a-z A-Z 0-9 - _ and space
    text = re.sub(r'[^a-zA-Z0-9_\- ]','', text)
    #No leading or trailing spaces
    text = text.strip()
    #No filenames > 200 characters (makes room for post ID and extention)
    if (len(text) > 200):
        text = text[:200]
    #Lead with an underscore if the filename isn't empty string
    if (len(text) > 0):
        text = "_" + text

    #return adjusted string
    return text

#Accepts an input file with thread URLs on each line, and redacts archived/deleted threads from the file as it encounters them
def saveThreads():
    infile = open('threads.txt','r')
    #Output file string (containing threads that aren't archived)
    output = ''
    for link in infile:
        link = link.strip()

        #Ignore blank lines
        if link:
            try:
                #If a thread returns false (indictating it doesn't exist or is now archived), remove it from the archive file
                print("-"*10 + link + "-"*10)
                t = saveThread(link)
                if t:
                    output += link + "\n"
                db.commit()
            except:
                #If there was a network or DB error, keep the link in the file just in case it was a temporary thing
                output += link + "\n"
    
    #Close and re-open the file in write mode, overwriting it with the still active thread addresses
    infile.close()
    infile = open('threads.txt','w')
    infile.write(output[:-1])
    infile.close()

#Run the script
saveThreads()
