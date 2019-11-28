# ntfsundelete-python-addon
parse and order the recovery information of ntfsundelete => recreating the folder structure

Background: I have actually used that script for myself. I accidentially moved my complete archive of documents from an external drive to another one, just to notice later that the data did not arrive! Since I used a move and not a copy, hundreds of documents and pictures were deleted. There are many recovery programs out there and you can find free ones, the problem is, that they offer you to restore each single file by click, and without folder structure. If you lost a whole archive of documents, the folder structure is part of the value! So I wrote that python script to recover a best guess folder structure of the deleted files and additional handy features. If you have many files that can be restored, you can have name conflicts because the folder structure cannot be restored exactly as it was, it has to be guessed. So this script has actually be used. Contact me if you have problems to use the script and I will create a better step by step guide! send2olaf at yahoo dot de

You can use Linux to undelete files on a NTFS drive / partition.
The program for this is ntfsundelete .
But with larger files and folders, it is not possible to recover the complete folder structure.
The information to do this is available, though.

Command to display the recoverable files on the partition:
ntfsundelete /dev/sdc2

Command to include details including the parent folder:
ntfsundelete /dev/sdc2 -v -P

will recover any file to a destination
ntfsundelete -u -m "*" -d "/root/recovery" /dev/sda1 



Using python creating a custom solution:

OK -- read the details in a json structure in python with the MTF Record as key
OK -- recreate the folder structure and check for double folder names
OK -- check the files and assign them to a unique folder (add the complete path to their info)
OK -- create a batch file to create the folder structure
OK -- create a batch file to create the files

the script is attached.

RE -- The python code is in the location xxx in the folder ntfsundelete
The python code works upon the information extracted by the linux programm ntfsundelete.
The basic information can be extracted, but the parent folder information is in the detail information.
The python code parses the information and can put it to json files.
There is a bit disorder in the code for treating the dictionary indices as text or integer.
I preferred integer but I missed that the import from a json file is text, though.
The first user friendly result is an csv-file with the youngest deletions on top.
The challenge was to derive a folder structure since the hierarchy needs to be rediscovered and there is error possible.
In the end the python script creates two scripts to be used on linux.
One to create the folder structure and another to restore the files there.
There can be more analysis and tries to:
-- check if the folder hierarchy can somehow be obtained better from the NTFS.
-- create a frontend
-- create a programm in other languages
-- try to create some kind of freeware program that beats the existing like puran and recuva.
The commercial versions of recovery software cost about 50 US$
