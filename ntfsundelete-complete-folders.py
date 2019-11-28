# -*- coding: utf-8 -*-
import re
import shodan
import json
import traceback
import sys
import itertools
import os
import hashlib
import time
import shutil
import codecs
import operator


class NTFS_Rescuer():
# 

# preconditions:	
# postconditions:	

	def __init__(self, destfolder):
		self.destfolder = destfolder
		self.checkfolder(destfolder)
	
	def checkfolder(self, destfolder):
		directory = destfolder
		if not os.path.exists(directory):
			os.makedirs(directory)
		
	def load_inodes_to_json(self, inputfile, jsonfile):
		
		inodesdic = {}	# dictionary to keep all the inodes
		pat_inode = re.compile(r'^MFT Record (\d+)')
		fin = open(inputfile, "r", encoding="utf-8")		
		# skip the first two lines
		next(fin)
		next(fin)
		data = fin.readlines()
		# initialize new entry
		content = []	
		
		for line in data:			
			if line == '\n':
				# processing collected entry content
				# find the inode and put it to dictionary
				for cc in content:
					groupmatch = pat_inode.match(cc)
					if groupmatch:
						iid = groupmatch.group(1)
						int(iid)
						#print(iid)
						inodesdic[iid] = content						
				# initialize new entry
				content = []	
			else:
				content.append(line.rstrip())		
		fin.close()
		print(">>> Inodes read in: ", str(len(inodesdic)))
		with codecs.open(jsonfile, 'w', encoding="utf-8") as file:
			json.dump(inodesdic, file)
		print(">>> Inodes transformed into json file.")
		
	def parse_json(self, jsonfile, parsedfile):
		
		patterns = {}
		patterns["recoverrate"] = re.compile(r'^File is (\d+)% recoverable')
		patterns["type"] = re.compile(r'^Type: (.+)')
		patterns["date"] = re.compile(r'^Date: (.+)')
		patterns["name"] = re.compile(r'^Filename: \(0\) (.+)')
		patterns["parent"] = re.compile(r'^Parent: (.+)')
		patterns["datec"] = re.compile(r'^Date C: (.+)')
		patterns["datea"] = re.compile(r'^Date A: (.+)')
		patterns["datem"] = re.compile(r'^Date M: (.+)')
		patterns["dater"] = re.compile(r'^Date R: (.+)')
		patterns["size"] = re.compile(r'^Size alloc: (\d+)')
		
				
		with codecs.open(jsonfile, 'r', encoding="utf-8") as fin:
			inodesdic = json.load(fin)
		for iid in inodesdic:
			newcontent = {}						
			newcontent["recoverrate"] = -1
			newcontent["type"] = ""
			newcontent["date"] = "1901-01-01 23:59" # using string as json serialization puts to string anyway
			newcontent["name"] = ""
			newcontent["parent"] = ""
			newcontent["datec"] = "1901-01-01 23:59"
			newcontent["datea"] = "1901-01-01 23:59"
			newcontent["datem"] = "1901-01-01 23:59"
			newcontent["dater"] = "1901-01-01 23:59"
			newcontent["size"] = -1
			
			for pp in patterns:
				for contentline in inodesdic[iid]:
				#print(contentline)				
					groupmatch = patterns[pp].match(contentline)
					if groupmatch:
						newcontent[pp] = groupmatch.group(1)
						break
		
			inodesdic[iid] = newcontent
		
		with codecs.open(parsedfile, 'w', encoding="utf-8") as file:
			json.dump(inodesdic, file)
		print(">>> Information parsed and parsed file produced.")
			
					
	def zzcleanupfiles(self):
		for subdir in self.subdirs:
			folder = self.destfolder + subdir
			for the_file in os.listdir(folder):
				file_path = os.path.join(folder, the_file)
				try:
					if os.path.isfile(file_path):
						os.unlink(file_path)
					#elif os.path.isdir(file_path): shutil.rmtree(file_path) # traverses also subdirectories
				except Exception as e:
					print (e)
	
	def create_folderfiles(self, parsedfile):
		with codecs.open(parsedfile, 'r', encoding="utf-8") as fin:
			inodesdic = json.load(fin)
		# ! Note: we are just handling folders here, no files to restore!
		### 1 - create parentfolders dictionary
		### 1 - => parentfolders[foldername][array of inodes with that name]
		### 2 - handle non-parent folders additionally
		### 2 - => parentfolders[zzz-------orphaned][list of inodes]	# here are folders (!) that do not have parents (root folders and others)
		### 2 - => parentfolders[<non-determined>]=[-1]		# folders whose parent information has possibly been lost
		### 2 - => parentfolders[.]=[-2]	# folders that are listed as in the current directory (.)
		### 3 - assign subfolders to potential parents, with ambiguity => take the closest inode candidate
		### 3 - => folders[inode][array of inodes of calculated subdirs]		
		### 4 - check if a complete folder structure can be created with all folders
		### 5 - Manual adjustments for loops in the folder structure: In our case the ambiguity was the 2sort folder that caused a loop,
		### ! it could be that this is the problem why the root cause, namely the manual move from a complete folder structure from one external drive to the other failed and caused the data to not be on the destination drive!
		### 6 - create the folder structure on destination folder and create a json file for the information to be used later
		
		
		### 1 - create parentfolders dictionary
		### 2 - handle non-parent folders additionally
		foldercount = 0
		parentfolders = {}
		nonparentfolders = {}	
		foldernames = {}
		folderset = set()
		for iid in inodesdic:
			if inodesdic[iid]["type"] == "Directory":
				foldercount += 1
				foldernames[iid] = inodesdic[iid]["name"]
				folderset.add(int(iid))
				parentname = inodesdic[iid]["parent"]
				if parentname != "":
					parentfolders[parentname] = []
				else:
					print("!!! Folder without parent information! Continuing.")
		parentfolders["<non-determined>"] = [-1]	# account for this folder that does not exist but is in the data if parent info vanished.
		parentfolders["."] = [-2]  # account for the current folder that does not have an inode but is in meta-data
		parentfolders["----non-parent----"] = []  # account for keeping processing information in one dictionary (important to not merge two dics later in 2)
		print(">>> Total folder count is: " + str(foldercount) + " plus the two with -1 and -2.")
		
		folders = {} # for file assignment to parent folder by name later
		for iid in inodesdic:
			if inodesdic[iid]["type"] == "Directory":
				foldername = inodesdic[iid]["name"]
				if not foldername in folders.keys():
					folders[foldername] = []
				folders[foldername].append(int(iid))
				if foldername in parentfolders.keys():
					parentfolders[foldername].append(int(iid))
				else:
					parentfolders["----non-parent----"].append(int(iid))
					if not foldername in nonparentfolders.keys():
						nonparentfolders[foldername] = []
					nonparentfolders[foldername].append(int(iid))
		folders["<non-determined>"] = [-1]	# account for this folder that does not exist but is in the data if parent info vanished.
		folders["."] = [-2]  # account for the current folder that does not have an inode but is in meta-data
		foldernames[-1] = "non-determined"
		foldernames[-2] = "current-folder"
					
		#with codecs.open("parentfolders.txt", 'w', encoding="utf-8") as outfile:
		#	for pf in parentfolders:
		#		outfile.write(pf + " :  " + str(parentfolders[pf]) + "\n")
		#	outfile.close()
		#print(">>> Parent folder file produced.")
		#with codecs.open("non-parentfolders.txt", 'w', encoding="utf-8") as outfile:
		#	for pf in nonparentfolders:
		#		outfile.write(pf + " :  " + str(nonparentfolders[pf]) + "\n")
		#	outfile.close()
		#print(">>> Non-Parent folder file produced.")
		with codecs.open("foldernames.txt", 'w', encoding="utf-8") as outfile:
			for pf in foldernames:
				outfile.write(str(pf) + " :  " + foldernames[pf] + "\n")
			outfile.close()
		with codecs.open("foldernames.json", 'w', encoding="utf-8") as file:
			json.dump(foldernames, file)
		with codecs.open("folders.json", 'w', encoding="utf-8") as file:
			json.dump(folders, file)
		print(">>> foldernames file produced.")
		
		### 3 - assign subfolders to potential parents, with ambiguity => take the closest inode candidate
		foldersNsubfolders = {}
				
		for pf in parentfolders:
			for iid in parentfolders[pf]:				
				foldersNsubfolders[iid] = []
				
		for iid in inodesdic:
			if inodesdic[iid]["type"] == "Directory":
				parentname = inodesdic[iid]["parent"]				
				iime = int(iid)
				if len(parentfolders[parentname]) == 1:
					reid = parentfolders[parentname][0]					
					foldersNsubfolders[reid].append(iime)					
				else:					
					aux = []
					for ii in parentfolders[parentname]:						
						#aux.append(abs(ii-iime))
						### 24464
						aux.append(ii)
					aux = sorted(aux, reverse=True)
					### !Beware ambigious parent folder problem. This below looks for the smaller but nearest inode of the potential parents.
					res = aux[-1]
					for aa in aux:						
						if aa < iime:
							res = aa
					####print(str(iime) + " ===> " + str(aa) + " among " + str(aux))					
					foldersNsubfolders[res].append(iime)
		
		with codecs.open("folders-subfolders.txt", 'w', encoding="utf-8") as outfile:
			for ff in foldersNsubfolders:
				outfile.write(str(ff) + " :  " + str(foldersNsubfolders[ff]) + "\n")
			outfile.close()
		print(">>> Subdirectories calculated and file produced.")
		
		### 4 - check if a complete folder structure can be created with all folders
		### using the -1 and -2 folders as root folders:
		folderset2 = set()
		def count_elements(currentfolder, folderdic, folderset2):			
			#print("x is : " + str(currentfolder))
			if len(currentfolder) == 0:
				return 1
			counter = 1			
			for f in currentfolder:
				folderset2.add(int(f))
				counter = counter + count_elements(folderdic[f], folderdic, folderset2)				
			return counter
		
		### 5 - Manual adjustments for loops in the folder structure:
		# 2sort is folder within fotos--Meltingpot, but also was a folder on high level.
		# => manipulating 2sort to the new folder 2sort-high:
		foldersNsubfolders[59797].remove(60140)
		foldersNsubfolders[99999] = [60140,-1,-2]
		folderset.add(99999)
		parentfolders["2sort-high"] = 99999
		
		#sys.setrecursionlimit(1000) # the default is just 1000, recursion error hints to a loop and inconstent data
		res = count_elements(foldersNsubfolders[-2], foldersNsubfolders, folderset2)
		res = res + count_elements(foldersNsubfolders[-1], foldersNsubfolders, folderset2)
		res = res + count_elements(foldersNsubfolders[99999], foldersNsubfolders, folderset2)
		print("count including all auxiliaries (-1, -2, and 99999) is: " + str(res))
		
		folderset3 = folderset - folderset2
		#print("Elements not in directory structure = ", folderset3)
		print("Original inode count plus auxiliary folders 99999 is: ", len(folderset)) 
		print("Elements count loop without auxiliaries: ", len(folderset2))
		diff = len(folderset3)
		print("Elements count diff: ", diff)
		if diff > 2:
			print("!! Ambiguity in folder structure.")
		print("Elements more in loop than in original folder list: " + str(folderset3))
		
		### 6 - create the folder structure on destination folder and create a json file for the information to be used later
		
		# work over the folder names to replace special characters
		# make them unique as well
		newfoldernames = {}
		newnames = set()
		filler = 0
		for iid in foldernames:
			newname = re.sub('[^A-Za-z0-9_-]', '-', foldernames[iid].lower()) # the lower takes care for case insensitive filesystem
			if newname in newnames:
				newname = str(filler) + newname
				#print(newname)
				filler = filler + 1		
			newfoldernames[int(iid)] = newname
			newnames.add(newname)
		print(">>> folder names changed for unique naming: " + str(filler))
		
		
							
		with codecs.open("foldernames-new.txt", 'w', encoding="utf-8") as outfile:
			for pf in newfoldernames:
				outfile.write(str(pf) + " :  " + newfoldernames[pf] + "\n")
			outfile.close()
		with codecs.open("foldernames-new.json", 'w', encoding="utf-8") as file:
			json.dump(newfoldernames, file)
		print(">>> foldernames-new file produced.")
		
		# create the folder structure		
		# complete loop is via root folders -1, -2 and 99999
		folderlist = {}		
				
		def build_foldernames(currentfolder, folderdic, foldername, make_folders):			
			if len(currentfolder) == 0:				
				return
			for iid in currentfolder:				
				currentfoldername = foldername + "/" + newfoldernames[iid]
				folderlist[int(iid)] = currentfoldername
				if make_folders:
					#print(currentfoldername)
					os.makedirs(currentfoldername)
				build_foldernames(folderdic[iid], folderdic, currentfoldername, make_folders)
			return
		
		# for really creating the folders on disk, put the last parameter to TRUE
		writetodisk = False
		if writetodisk:
			destfolder = destfolder + "RRR"
		else: # use to create mkdir batch file
			destfolder = "/media/lilly2/zz-recover"
			
		build_foldernames(foldersNsubfolders[99999], foldersNsubfolders, destfolder, writetodisk)
				
		sorted_folderlist = sorted(folderlist.items(), key=operator.itemgetter(1)) # sort dictionary by values, but it creates a list of tuples
		
		checkset = set()
		#print(sorted_folderlist)
		for n in sorted_folderlist:
			checkset.add(n[1])
			#print(n[1])
		print("compare: " + str(len(checkset)) + " vs. " + str(len(sorted_folderlist)))
		
		with codecs.open("folderpaths-new.txt", 'w', encoding="utf-8") as outfile:
			for pf in sorted_folderlist:
				outfile.write(str(pf[0]) + " :  " + pf[1] + "\n")
			outfile.close()
		with codecs.open("folderpaths-new.json", 'w', encoding="utf-8") as file:
			json.dump(folderlist, file)
		print(">>> folderpaths-new file produced.")
		
	def create_restore_program(self, parsedfile):
		inodesdic = {}
		with codecs.open(parsedfile, 'r', encoding="utf-8") as fin:
			inodesdic = json.load(fin)
	
		### 1 - filter files to restore and create files for manual inspection, newest files first, create export to be used in excel.
		### 2 - Identify the affected folders and if they are present and create relation folder-file and file-ownpath.		
		### 3 - Create a batch file		
		
		### 1 - filter files to restore and create files for manual inspection, create export to be used in excel.
		files2restore = {}
		filesbydate = {}
		#recoverrates = set()
		totalsize = 0
		for iid in inodesdic:
			if inodesdic[iid]["type"] == "File":
				if inodesdic[iid]["recoverrate"] == "100":
					files2restore[iid] = inodesdic[iid]
					filesbydate[iid] = inodesdic[iid]["date"]
					totalsize = totalsize + int(inodesdic[iid]["size"])
				#if inodesdic[iid]["recoverrate"] not in recoverrates:
				#	recoverrates.add(inodesdic[iid]["recoverrate"])
		totalsize = totalsize // 1024 // 1024 # MB
		
		print(">>> files to restore identified: " + str(len(files2restore)))
		print(">>> their total size is about in MB: " + str(totalsize))
		sorted_filesbydate = sorted(filesbydate.items(), key=operator.itemgetter(1), reverse=True)
		#sorted_filesbydate = filesbydate.sort(key=lambda x: time.strptime(x, '%Y-%m-%d %H:%M:%S')[0:6], reverse=True)
		#print(str(len(sorted_filesbydate)))
		
		with codecs.open("filesbydate.txt", 'w', encoding="utf-8") as outfile:
			for pf in sorted_filesbydate:
				outfile.write(str(pf[0]) + " :  " + pf[1] + "\n")
			outfile.close()
		print(">>> filesbydate file produced, newest to oldest.")
		
		filesbyname = {}
		for iid in filesbydate:
			filesbyname[iid] = inodesdic[iid]["name"]
		with codecs.open("filesbyname.txt", 'w', encoding="utf-8") as outfile:
			for pf in filesbyname:
				outfile.write(str(pf) + " :  " + filesbyname[pf] + "\n")
			outfile.close()
		print(">>> filesbyname file produced, newest to oldest.")	
		
		# create file of files to be restored to be opened in excel
		pat_ext = re.compile(r'.+(\.[a-zA-Z0-9]+)$') 
		for iid in files2restore:
			file_extension = pat_ext.match(files2restore[iid]["name"])
			if file_extension:
				files2restore[iid]["ext"] = file_extension.group(1)
			else:
				files2restore[iid]["ext"] = "none"
		
		with codecs.open("files2restore.txt", 'w', encoding="utf-8") as outfile:
			# create header line
			# someitem = next(iter(files2restore.values()))
			headers = ("date", "datea", "dater", "datec", "datem", "size", "ext", "name", "parent", "recoverrate", "type") 
			for key in headers:
				outfile.write(key + "\t")
			outfile.write("noteid")
			outfile.write("\n")
			# process content
			for iidtuple in sorted_filesbydate: # we take the order of the iids by date
				for key in headers:
					outfile.write(files2restore[iidtuple[0]][key] + "\t")
				outfile.write(iidtuple[0])
				outfile.write("\n")
			outfile.close()
		print(">>> files2restore.txt produced, newest to oldest.")
		print(">>> \tThis file can be used to manually find the most important files and restore them by inode.")	
		
		
		### 2 - Identify the affected folders and if they are present and create relation folder-file and file-ownpath.		
				
		folderlist = {}
		with codecs.open("folderpaths-new.json", 'r', encoding="utf-8") as fin:
			folderlist = json.load(fin)
			
		folders = {}
		with codecs.open("folders.json", 'r', encoding="utf-8") as fin:
			folders = json.load(fin)
		
		foldersNfiles = {}
		for iid in folderlist:
			foldersNfiles[int(iid)] = []
		foldersNfiles[-1] = []
		foldersNfiles[-2] = []
		
		filesNpaths = {}
		
		for iidtuple in sorted_filesbydate:			
			parent = files2restore[iidtuple[0]]["parent"]
			if not parent in folders.keys():				
				print("!!!  folder not known by folder list: " + parent )
			# assign files to folders
			if len(folders[parent]) == 1:
					folderid = folders[parent][0]										
			else:					
				aux = []
				for ii in folders[parent]:						
					aux.append(ii)
				aux = sorted(aux, reverse=True)
				### !Beware ambigious parent folder problem. This below looks for the smaller but nearest inode of the potential parents.
				res = aux[-1]
				iime = int(iidtuple[0])
				for aa in aux:						
					if aa < iime:
						res = aa
				####print(str(iime) + " ===> " + str(aa) + " among " + str(aux))
				folderid = res
			foldersNfiles[folderid].append(int(iidtuple[0]))
			folderpath = folderlist[str(folderid)]
			filename = files2restore[iidtuple[0]]["name"] # filename not needed in path, is a separate parameter in the ntfsundelete command on linux
			filesNpaths[int(iidtuple[0])] =  folderpath
			
		with codecs.open("folders-files.txt", 'w', encoding="utf-8") as outfile:
			for ff in foldersNfiles:
				outfile.write(str(ff) + " :  " + str(foldersNfiles[ff]) + "\n")
			outfile.close()
		with codecs.open("filesNpaths.json", 'w', encoding="utf-8") as file:
			json.dump(filesNpaths, file)
		print(">>> All parent directories of files found in list and files produced: \n folder-files.txt\nfilesNpaths.json")
		
		### 3 - Create a batch file	for linux
		#destpath="/mnt/export/recovery/" # must be created in the folder script section before
		sourcedevice="/dev/sdd2"
		mainfolder = ""
		
		with codecs.open("restoreall.sh", 'w', encoding="utf-8") as outfile:
			outfile.write("#!/bin/bash\n")
			for iid in sorted_filesbydate:
				filename = files2restore[iid[0]]["name"]
				destinationfolder = mainfolder + filesNpaths[int(iid[0])]
				fullpath = destinationfolder + "/" + filename
				outputstring = "ntfsundelete " + sourcedevice + " -u -i " + iid[0] + " -o \"" + filename + "\" -d " + destinationfolder + " && echo \"" + fullpath + "\" >> ./success.txt || echo \"" + fullpath + "\" >> ./failed.txt"
				outfile.write(outputstring + "\n")
			outfile.close()
		print(">>> A linux executable has been produced.")
		
		# create a linux exectable to make the folders
		with codecs.open("create-folders.sh", 'w', encoding="utf-8") as outfile:
			outfile.write("#!/bin/bash\n")
			folders = []
			for iid in folderlist:				
				outputstring = "mkdir \"" + folderlist[iid] + "\""
				folders.append(outputstring)
			folders = sorted(folders)
			for ff in folders:
				outfile.write(ff + "\n")
			outfile.close()
		print(">>> A linux executable for folder creation has been produced.")
		
try:
	
	destfolder = '/media/lilly2/zz-recover'
	inputfile = './recovery/2.txt'
	jsonfile = './recovery/inodes.json'
	parsedfile = './recovery/inodes-filtered.json'
	
	# runtime action
	Rescuer = NTFS_Rescuer(destfolder)
	#Rescuer.load_inodes_to_json(inputfile, jsonfile)
	#Rescuer.parse_json(jsonfile, parsedfile)
	Rescuer.create_folderfiles(parsedfile)
	Rescuer.create_restore_program(parsedfile)
	

except:
	print(traceback.format_exc())