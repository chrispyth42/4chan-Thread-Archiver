# 4chan-Thread-Archiver
threadSaver.py takes a list of 4chan thread URLs specified in threads.txt (one per line), and archives them into an sqlite database. It also downloads all images in those threads into an 'images' folder in the current directory. I don't use 4chan very much, and was a bit iffy about posting a script that interfaces with the site here (given its reputation). But it was a great exercise! Especially with how neatly they offer up their site for people who want to code it

Be sure to follow the API rules when running this though. The main rule pertaining to this script is just not calling the API JSON version of a thread more than once every 10 seconds (which shouldn't be an issue)
https://github.com/4chan/4chan-API
