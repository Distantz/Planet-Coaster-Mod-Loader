import tkinter as tk
import shutil
import configparser
import pcm
from tkinter import ttk
from tkinter import font
from tkinter.filedialog import askopenfilename, askdirectory, askopenfilenames
from tkinter import messagebox
from tkinter import simpledialog

import sys
from os import path, mkdir, rename
from shutil import copy, copyfile
from json import dump, loads, load
from zipfile import ZipFile

from util import widgets
from modules import inject
from generated.formats.ovl import OvlFile

class Mod():
    def __init__(self, gui):
        self.gui = gui
        self.OVLs = []
        global dir_path
        dir_path = path.dirname(path.realpath(__file__)).replace("\\", "/")

    def loadMeta(self, filepath):
        with ZipFile(filepath) as zipfile:
            with zipfile.open("mod.json") as jsonFile:
                self.metaData = loads(jsonFile.read())
                self.modName = (self.metaData["meta"]["Name"])
                self.modAuthor = (self.metaData["meta"]["Author(s)"])
                self.modDesc = (self.metaData["meta"]["Desc"])

    def save(self):
        with open("Data/mods.json", "r") as file_r:
            tempdata = file_r.read()
            if len(tempdata) == 0:
                self.modData = {}
            else:
                self.modData = loads(tempdata)
        self.modData[self.modName] = {}
        self.modData[self.modName] = ({
            "Name" : self.modName,
            "Author" : self.modAuthor,
            "Desc" : self.modDesc,
            "Backups" : self.backupPaths,
            "OVLs" : self.OVLs
            })
        print(self.modData)
        with open("Data/Mods.json", "w") as file:
            dump(self.modData, file)

    def uninstall(self):
        #self.gui.modList.pop(self.gui.modList.index(self))
        for i,backup  in enumerate(self.backupPaths):
            self.backuppath = self.gui.planetCoasterDir + "/backups/" + backup.replace("/","]")
            #print(self.backuppath)
            shutil.copyfile(self.backuppath, self.gui.planetCoasterDir + "/" + self.OVLs[i])
            if path.exists(self.backuppath[:-1]+"s"):
                shutil.copyfile(self.backuppath[:-1]+"s", self.gui.planetCoasterDir + "/" + self.OVLs[i][:-1]+"s")

        print("bonked {}".format(self.modName))

        with open("Data/Mods.json", "r") as file_r:
            tempdata = file_r.read()
            if len(tempdata) == 0:
                self.modData = {}
            else:
                self.modData = loads(tempdata)
            self.modData.pop(self.modName, None)

            with open("Data/Mods.json", "w") as file:
                dump(self.modData, file)
        self.gui.modList.pop(self.gui.modList.index(self))

        #print("backup {}".format(self.getBackupPathDestination(self.backupPath)))
        #restore(self.gui, self.getBackupPathDestination(self.backupPath))

    def install(self, filepath):
        with ZipFile(filepath) as zipfile:
            with zipfile.open("mod.json") as jsonFile:

                self.mod = load(jsonFile)

                self.modName = (self.mod["meta"]["Name"])
                self.modAuthor = (self.mod["meta"]["Author(s)"])
                self.modDesc = (self.mod["meta"]["Desc"])

                for self.path, self.files in self.mod["Files"].items():
                    self.temppath = "Data/temp-files"
                    try:
                        mkdir(self.temppath)
                    except:
                        pass

                    self.backupPaths = []
                    self.backupPath = self.path[self.path.find("Win64"):]
                    self.backupPaths.append(self.backupPath)
                    self.backup(self.backupPath)

                    self.filesTemp = []
                    for self.file in self.files:
                        #Major sanitisation required
                        self.sanitised_path = self.path.replace("/","_")
                        self.sanitised_path = self.sanitised_path.replace(":", "#") #Needed?
                        self.sanitised_path = self.sanitised_path[self.sanitised_path.find("Win64"):]

                        self.sanitised_file = self.file.split("\\")
                        self.name = self.sanitised_path + "/" + self.sanitised_file[-1]

                        print("NAME: " + self.name)
                        print("TEMPPATH + "+self.temppath)

                        zipfile.extract(self.name, path=self.temppath)

                        self.fileSplit = self.file.rsplit("\\",1)
                        self.file = "{}/{}/{}/{}".format(dir_path, self.temppath, self.sanitised_path, self.file)
                        print("File: " + self.file)
                        self.filesTemp.append(self.file)

                    self.ovlPath = self.gui.planetCoasterDir + "/" + self.path

                    self.OVLs.append(self.backupPath)
                    #self.save()
                    self.inject_files(self.ovlPath, self.filesTemp)
                    shutil.rmtree(self.temppath)

    def inject_files(self, path, files):
        self.ovl_data = OvlFile()
        self.ovl_data.load(path)
        inject.inject(self.ovl_data,files, False, False)
        self.ovl_data.save(path)

    def backup(self, relativeFilepath):
        try:
            mkdir(self.gui.planetCoasterDir + "/backups/")
        except:
            pass

        self.directory = self.gui.planetCoasterDir + "/" + relativeFilepath
        self.destination = self.getBackupPathDestination(relativeFilepath)

        self.ovsDir = self.directory[:-1] + "s"
        self.ovsDestination = self.getBackupPathDestination(relativeFilepath)[:-1] + "s"

        if path.exists(self.destination):
            shutil.copyfile(self.directory, self.destination)
        else:
            pass

        if path.exists(self.ovsDir):
            shutil.copyfile(self.ovsDir, self.ovsDestination)

    def getBackupPathDestination(self, relativeFilepath):
        self.backupOVLPath ="{}\{}".format(self.gui.planetCoasterDir + "/backups", relativeFilepath.replace("/", "]").replace("\\" , "]").replace(":","#"))
        return self.backupOVLPath
