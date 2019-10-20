# 4chan-Thread-Archiver
threadSaver.py takes a list of 4chan thread URLs specified in threads.txt (one per line), and archives them into an sqlite database. It also downloads all images in those threads into an 'images' folder in the current directory. I don't use 4chan very much, and was a bit iffy about posting a script that interfaces with the site here (given its reputation). But it was a great exercise! Especially with how neatly they offer up their site for people who want to code it

It was a good challenge! Trying to come up with a schema to house thier JSON, and write it in a way that's efficient to query. The schema of the database is as follows:

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
    )
    
    CREATE TABLE IF NOT EXISTS Posts (
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
    )

-----------------------------------------------------------------------------------------------------------------------------

The 'Threads' table contains metadata about the thread. Such as how many unique IP addresses have posted to it, how many replies it has, etc. This data is all stored within the first 'post' object of each thread, and is updated every time the script makes a call to a thread

-----------------------------------------------------------------------------------------------------------------------------

The 'Posts' table contains every post object that has been retrieved from all input threads (post objects are immutable). The interesting part of designing this table was figuring out how to query it without costing too much performance as it grows in size. The solution I came up with was this query:

        SELECT MAX(ID) FROM Posts
        WHERE Board = (board) AND ParentID = (threadID)

Because post IDs only increment, it's possible to test if a post exists in a given thread by making 1 query for the maximum post ID currently in the database for that thread, and compare incoming post IDs to that integer in order to determine if they exist in the database

-----------------------------------------------------------------------------------------------------------------------------

The function that handles the input file isn't too complicated, but apart from reading in the file, it also handles removing thread URLs from the input file once the they either become archived (becoming immutable), or are deleted from 4chan. This eliminates unnecessary requests, and allows this script to manage itself if assigned to a CRON job

-----------------------------------------------------------------------------------------------------------------------------

Be sure to follow the API rules when running this though. The main rule pertaining to this script is just not calling the API JSON version of a thread more than once every 10 seconds (which shouldn't be an issue)
https://github.com/4chan/4chan-API
