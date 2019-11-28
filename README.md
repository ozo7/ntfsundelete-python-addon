# ntfsundelete-python-addon
parse and order the recovery information of ntfsundelete => recreating the folder structure

Here is the basic information

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
The commercial version costs about 50 US$
