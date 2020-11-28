import tkinter as tk
import os
import shutil
import configparser
import pcm
from tkinter import ttk
from tkinter import font
from tkinter.filedialog import askopenfilename, askdirectory, askopenfilenames
from tkinter import messagebox
from tkinter import simpledialog

from TkinterDnD2 import *

import shutil
import json
from zipfile import ZipFile 
from pyffi_ext.formats.ovl import OvlFormat
from pyffi_ext.formats.ms2 import Ms2Format

from util import widgets
from modules import extract, inject, hasher, walker
from generated.formats.ovl import OvlFile


"""
Ill just say it quickly, yes!

this is very messy code lol

but i'll clean it up into Defs when i'm done with the
early experiments
"""
class Gui():

    def __init__(self):

        self.setupGui()

    def setupGui(self):

        self.mainWindow = tk.Tk()

        self.mainWindow.geometry("400x800+600+350")
        self.mainWindow.title("Planco Mod Manager")

        global dir_path

        dir_path = os.path.dirname(os.path.realpath(__file__)).replace("\\", "/")
        print(dir_path)

        self.styles()

        self.mainWindow.tk.eval("""
        set base_theme_dir {}/awthemes-9.3.1/
        
        package ifneeded awthemes 9.3.1 \
            [list source [file join $base_theme_dir awthemes.tcl]]
        package ifneeded colorutils 4.8 \
            [list source [file join $base_theme_dir colorutils.tcl]]
        package ifneeded awdark 7.7 \
            [list source [file join $base_theme_dir awdark.tcl]]
        package ifneeded awlight 7.6 \
            [list source [file join $base_theme_dir awlight.tcl]]
        """.format(dir_path))

        self.mainWindow.tk.call("package", "require", 'awdark')
        self.mainWindow.tk.call("package", "require", 'awlight')

        self.style.theme_use('awdark')

        self.mainWindow.configure(bg=self.style.lookup('TFrame', 'background'))

        self.mainWindow.grid_columnconfigure(0, weight=1)
        self.mainWindow.grid_rowconfigure(0, weight=1)

        #self.entry_sv = tk.StringVar()
        #self.entry = tk.Entry(self.mainWindow, textvar=self.entry_sv, width=80)
        #self.entry.pack(fill=tk.X)
        #self.entry.drop_target_register(DND_FILES)
        #self.entry.dnd_bind('<<Drop>>', self.drop)

        self.tabs = ttk.Notebook(self.mainWindow, takefocus=False)
        self.tabs.grid(row=0, column=0, sticky="NSEW")

        self.manageModsFrame = ttk.Frame(self.tabs)
        self.manageModsFrame.grid_columnconfigure(0, weight=1)
        self.manageModsFrame.grid_columnconfigure(1, weight=1)

        self.packModFrame = ttk.Frame(self.tabs)
        self.packModFrame.grid_columnconfigure(0, weight=1)
        self.packModFrame.grid_rowconfigure(1, weight=1)

        self.tabs.add(self.manageModsFrame, text="Manage", sticky="nsew")
        self.tabs.add(self.packModFrame, text="Export", sticky="nsew")

        self.manageModsLabel = ttk.Label(self.manageModsFrame, text="Manage Mods", font=self.headerFont, anchor="center")
        self.manageModsLabel.grid(row=0, column=0, sticky="NEW", columnspan=2)

        self.manageModsInstallButton = ttk.Button(self.manageModsFrame, text="Install", command= lambda: inject_mod(self, askopenfilename(initialdir = dir_path+"/Mods")))
        self.manageModsInstallButton.grid(row=1, column=0, sticky="e")

        self.manageModsRestoreButton = ttk.Button(self.manageModsFrame, text="Restore", command= lambda: restore(self))
        self.manageModsRestoreButton.grid(row=1, column=1, sticky="w")

        self.exportModsLabel = ttk.Label(self.packModFrame, text="Pack PCM", font=self.headerFont, anchor="center")
        self.exportModsLabel.grid(row=0, column=0, sticky="NEW")

        self.exportModCanvasFrame = tk.Frame(self.packModFrame, bg=self.style.lookup('TButton', 'background'), highlightbackground=self.style.lookup('TButton', 'bordercolor'), highlightthickness=2)
        self.exportModCanvasFrame.grid(row=1, column=0, sticky="nsew")

        self.exportModCanvasFrame.grid_columnconfigure(0, weight=1)

        self.exportModToolbarFrame = ttk.Frame(self.packModFrame)
        self.exportModToolbarFrame.grid(row=2, column=0, sticky="nsew")

        self.exportModCreateNew = ttk.Button(self.exportModToolbarFrame, text="Add New", command = lambda: self.createNewExportFile(self))
        self.exportModExport = ttk.Button(self.exportModToolbarFrame, text="Pack", command = lambda: self.pack())

        self.exportModCreateNew.grid(row=0, column=0, sticky="wns")
        self.exportModExport.grid(row=0, column=2, sticky="ens")

        self.exportModToolbarFrame.grid_columnconfigure(0, weight=1)
        self.exportModToolbarFrame.grid_rowconfigure(0, weight=1)
        self.exportModToolbarFrame.grid_columnconfigure(2, weight=1)

        self.packModFrame.grid_rowconfigure(2, weight=0, minsize=45)

        self.tabs.bind("<<NotebookTabChanged>>", lambda event:self.mainWindow.focus_set())

        for widget in self.manageModsFrame.winfo_children():

            widget.bind("<1>", lambda event:self.mainWindow.focus_set())
           
        for widget in self.exportModCanvasFrame.winfo_children():

            if widget.winfo_class() == "Entry":

                widget.bind("<1>", lambda event:widget.focus_set())
           
        self.config()

        self.mainWindow.mainloop()

    def drop(event):
        self.entry_sv.set(event.data)

    def createNewExportFile(self, gui):

        if not hasattr(self, 'exportFileList'):

            self.exportFileList = []

        fileDir = askopenfilenames(initialdir = dir_path)
        #ovlDir = askopenfilename(initialdir = gui.planetCoasterDir)
        ovlDir = ""

        for file in fileDir:
            self.exportFileList.append(ChangedFiles(self, self.exportModCanvasFrame, len(self.exportFileList), 0, ovlDir, file))
            self.exportFileList[-1].entryVar.set(ovlDir)

    def styles(self):

        self.style = ttk.Style(self.mainWindow)
        self.headerFont = font.Font(size=20, weight='bold')

    def config(self):

        self.config = configparser.ConfigParser()
        self.config.read("Data/config.ini")

        self.planetCoasterDir = self.config["DEFAULT"]["GameDirectory"]


        if self.config["DEFAULT"]["HasSetup"] != "True":

            self.planetCoasterDir = messagebox.showinfo("Welcome!", "Please select your Planet Coaster installation folder (usually found in the Steamgames folder)") 

            while True:

                self.planetCoasterDir = askdirectory()

                if self.planetCoasterDir.split("/")[-1] != "Planet Coaster":

                    messagebox.showerror("Error", "Not a valid Planet Coaster directory!")

                else:
                    break

            #os.mkdir(self.planetCoasterDir + "\\backups")
            self.config["DEFAULT"] = {
                "GameDirectory": self.planetCoasterDir, "HasSetup": True}
            
            with open("Data/config.ini", "w") as configfile:
                self.config.write(configfile)

    def pack(self):

        self.modName = simpledialog.askstring(title="Test", prompt="Name: ")

        self.Meta = pcm.meta("Jan","Evan","AHH")

        self.out = {}
        self.out["Files"] = {}
        self.temp = sorted(self.exportFileList, key=lambda x: x.ovlFile, reverse=True)
        for i,self.test in enumerate(self.temp):
            self.OVLPath = self.exportFileList[i].entryVar.get()
            self.shortenedOVLPath = self.OVLPath[self.OVLPath.find("Win64"):]
            self.out["Files"][self.shortenedOVLPath] = []

        for self.test in self.temp:
            self.shortenedOVLPath = self.shortenedOVLPath[self.shortenedOVLPath.find("Win64"):]
            self.out["Files"][self.shortenedOVLPath].append((self.test.file.rsplit("/",1)[1]))

        self.saveDir = "Mods/" + self.modName
        try:
            os.mkdir(self.saveDir)
        except:
            pass
        self.Meta = pcm.meta("Jan","Evan","AHH")
        self.PCM = pcm.pcm(self.out, self.Meta)
        self.PCM.write_meta()
        self.PCM.write_pcm()
        self.PCM.pcm_write_to_file(self.saveDir)

        for self.test in self.temp:
            self.shortenedOVLPath = self.shortenedOVLPath[self.shortenedOVLPath.find("Win64"):]
            self.dirName = self.shortenedOVLPath.replace("\\","_")
            self.dirName = self.dirName.replace(":","#")
            print(self.saveDir + "/" + self.dirName)
            try:
                os.mkdir(self.saveDir + "/" + self.dirName)
            except:
                pass
            shutil.copyfile(self.test.file, self.saveDir + "/" + self.dirName + "/" +self.test.file.split("/")[-1])

        shutil.make_archive(self.saveDir, 'zip', self.saveDir)
        os.rename(self.saveDir + ".zip", self.saveDir + ".pcm")
        shutil.rmtree(self.saveDir)


        #for self.file in self.exportFileList:
            #if self.file.ovlFile not in self.checker:
                #self.checker.append(self.file.ovlFile)
            #value = (self.file.ovlFile + "#" + self.file.file)

#Evan Func
def inject_files(path, files):
    ovl_data = OvlFile()
    ovl_data.load(path)
    inject.inject(ovl_data,files, False, False)
    ovl_data.save(path)


def inject_mod(gui, filepath):
    with ZipFile(filepath) as zip:
        with zip.open("mod.json") as jsonFile:

            mod = json.load(jsonFile)

            print(mod["meta"])

            for path, files in mod["Files"].items():
                temppath = "Data/temp-files"
                try:
                    os.mkdir(temppath)
                except:
                    pass

                filesTemp = []
                for file in files:
                    #Major sanitisation required
                    count = path.count("\\")
                    sanitised_path = path.replace("\\","_")
                    sanitised_path = sanitised_path.replace(":", "#")
                    sanitised_path = sanitised_path[sanitised_path.find("Win64"):]

                    sanitised_file = file.split("\\")
                    name = sanitised_path + "/" + sanitised_file[-1]

                    zip.extract(name, path=temppath)

                    #print("PATH AGAIN: " + str(file.rsplit("/",1)))
                    fileSplit = file.rsplit("\\",1)
                    #file = fileSplit[0] + "/" + temppath + "/" + sanitised_path + "/" + fileSplit[1]
                    file = dir_path + "/" + temppath + "/" + sanitised_path + "/" + file
                    print("File: " + file)
                    filesTemp.append(file)

                ovlPath = gui.planetCoasterDir + "/" + path
                #print("PATH AGAIN: " + str(filesTemp))
                inject_files(ovlPath, filesTemp)

                shutil.rmtree(temppath)


def restore(gui):

    backupFileDir = "{}/{}".format(gui.planetCoasterDir, "backups/")

    for filename in os.listdir(backupFileDir):

        with open("{}{}".format(backupFileDir,filename), "rb") as fileData:

            data = fileData.read()
            replacePlanetcoasterFile(gui, filename, data)

def replacePlanetcoasterFile(gui, relativeFilepath, data):

    destination ="{}\{}".format(gui.planetCoasterDir, relativeFilepath.replace("_", "/"))

    with open(destination, "wb") as file:

        file.write(data)

        file.close()


def backupPlanetcoasterFile(gui, relativeFilepath):


    directory = gui.planetCoasterDir + "/" + relativeFilepath
    destination ="{}\{}\{}".format(dir_path, "/data/backups/", relativeFilepath.replace("/", "_"))

    if not os.path.exists(destination):

        shutil.copyfile(directory, destination)

    else:

        messagebox.showerror(gui.mainWindow, message = "Error:\nConflict detected! Mod changes file of another mod (this can cause loss of mod functionality/features)")


class ChangedFiles():

    def __init__(self, gui, parent, row, column, ovlFile, file):

        self.gui = gui
        self.file = file
        self.ovlFile = ovlFile
        self.frame = ttk.Frame(parent)
        self.frame.grid_columnconfigure(0, weight=0, uniform="title", minsize=135)
        self.frame.grid_columnconfigure(1, weight=1, uniform="dir")

        self.directoryLabel = ttk.Label(self.frame, text = file.split("/")[-1])

        self.entryVar = tk.StringVar()

        self.entryLabel = ttk.Entry(self.frame, exportselection=0, textvariable=self.entryVar)

        self.entryLabel.bind("<1>", lambda event:self.entryLabel.focus_set())
        self.destroyButton = tk.Button(self.frame, text="×", bg="#c23b15", highlightbackground="#FFFFFF", command=lambda: self.destroy())
        self.frame.grid(row=row, column=column, sticky="ew")
        self.directoryLabel.grid(row=0, column=0, sticky="nsw")
        self.entryLabel.grid(row=0, column=1, sticky="nsew")
        self.destroyButton.grid(row=0, column=2, sticky="nse")

    def destroy(self):

        self.frame.destroy()
        self.gui.exportFileList.pop(self.gui.exportFileList.index(self))



gui = Gui()

        
