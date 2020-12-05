import tkinter as tk
import shutil
import configparser
import pcm
from tkinter import ttk
from tkinter import font
from tkinter.filedialog import askopenfilename, askdirectory, askopenfilenames
from tkinter import messagebox
from tkinter import simpledialog

from PyQt5 import QtGui, QtCore, QtWidgets

from mod import Mod

from os import path, mkdir, rename
from shutil import copy, copyfile
from json import dump, loads
from zipfile import ZipFile

from util import widgets

from modules import inject
from generated.formats.ovl import OvlFile

from updater import Updater

class Gui():

    def __init__(self):
        self.setupGui()


    def setupGui(self):

        self.mainWindow = tk.Tk()

        self.mainWindow.geometry("400x800+600+350")
        self.mainWindow.title("PC Mod Manager")

        self.modList = self.loadModsList()

        global dir_path

        dir_path = path.dirname(path.realpath(__file__)).replace("\\", "/")

        self.mainWindow.iconbitmap(dir_path + '/Data/icon.ico')

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

        self.tabs = ttk.Notebook(self.mainWindow, takefocus=False)
        self.tabs.grid(row=0, column=0, sticky="NSEW")

        self.manageModsFrame = ttk.Frame(self.tabs)
        self.manageModsFrame.grid_columnconfigure(0, weight=1)
        self.manageModsFrame.grid_columnconfigure(1, weight=1)
        self.manageModsFrame.grid_rowconfigure(1, weight=1)

        self.packModFrame = ttk.Frame(self.tabs)
        self.packModFrame.grid_columnconfigure(0, weight=1)
        self.packModFrame.grid_rowconfigure(1, weight=1)

        self.tabs.add(self.manageModsFrame, text="Manage", sticky="nsew")
        self.tabs.add(self.packModFrame, text="Export", sticky="nsew")

        self.manageModsLabel = ttk.Label(self.manageModsFrame, text="Manage Mods", font=self.headerFont, anchor="center")
        self.manageModsLabel.grid(row=0, column=0, sticky="NEW", columnspan=2)

        self.manageModsScrollFrame = ScrollableFrame(self.manageModsFrame, self)
        self.manageModsScrollFrame.grid(row=1, column=0, sticky="NESW", columnspan=2)

        self.modWidgetList = []
        for i, mod in enumerate(self.modList):
            widget = ModTileWidget(mod, self, self.manageModsScrollFrame.scrollable_frame, i, 0)
            self.modWidgetList.append(widget)


        self.manageModsButtonFrame = ttk.Frame(self.manageModsFrame)
        self.manageModsButtonFrame.grid(row=2, column=0, columnspan=2, sticky="nsew")

        self.manageModsButtonFrame.grid_columnconfigure(0, weight=0, uniform="button")
        self.manageModsButtonFrame.grid_columnconfigure(1, weight=0, uniform="button")
        self.manageModsButtonFrame.grid_columnconfigure(2, weight=0, uniform="button")

        self.manageModsInstallButton = ttk.Button(self.manageModsButtonFrame, text="Install new mod", command= lambda: self.inject_mod(askopenfilename(initialdir = dir_path+"/Mods")))
        self.manageModsInstallButton.grid(row=0, column=0, sticky="nsew")

        self.manageModsRestoreButton = ttk.Button(self.manageModsButtonFrame, text="Uninstall all mods", command= lambda: self.restore())
        self.manageModsRestoreButton.grid(row=0, column=1, sticky="nsew")

        self.manageModsLaunchGameButton = ttk.Button(self.manageModsButtonFrame, text="Launch Planet Coaster", command=lambda: subprocess.run("cmd /c start steam://run/493340"))
        self.manageModsLaunchGameButton.grid(row=0, column=2, sticky="nsew")



        self.exportModsLabel = ttk.Label(self.packModFrame, text="Pack PCM", font=self.headerFont, anchor="center")
        self.exportModsLabel.grid(row=0, column=0, sticky="NEW")

        self.exportModCanvasFrame = ScrollableFrame(self.packModFrame, self)
        self.exportModCanvasFrame.grid(row=1, column=0, sticky="nsew")

        self.exportModCanvasFrame.grid_columnconfigure(0, weight=1)

        self.exportModMetaFrame = ttk.Frame(self.packModFrame)
        self.exportModMetaFrame.grid(row=2, column=0, sticky="nsew")

        self.metaNameLabel = ttk.Label(self.exportModMetaFrame, text="Name:", font = font.Font(size=11, weight="bold"))
        self.metaNameEntry = ttk.Entry(self.exportModMetaFrame)

        self.metaDescLabel = ttk.Label(self.exportModMetaFrame, text="Description:", font = font.Font(size=11, weight="bold"))
        self.metaDescEntry = ttk.Entry(self.exportModMetaFrame)

        self.metaAuthLabel = ttk.Label(self.exportModMetaFrame, text="Author(s):", font = font.Font(size=11, weight="bold"))
        self.metaAuthEntry = ttk.Entry(self.exportModMetaFrame)

        self.metaNameLabel.grid(row=0, column=0, sticky="nsew")
        self.metaNameEntry.grid(row=1, column=0, sticky="nsew")
        self.metaDescLabel.grid(row=2, column=0, sticky="nsew")
        self.metaDescEntry.grid(row=3, column=0, sticky="nsew")
        self.metaAuthLabel.grid(row=4, column=0, sticky="nsew")
        self.metaAuthEntry.grid(row=5, column=0, sticky="nsew")

        self.exportModMetaFrame.grid_columnconfigure(0, weight=1)

        self.exportModToolbarFrame = ttk.Frame(self.packModFrame)
        self.exportModToolbarFrame.grid(row=3, column=0, sticky="nsew")

        self.exportModCreateNew = ttk.Button(self.exportModToolbarFrame, text="Add File", command = lambda: self.createNewExportFile())
        self.exportModExport = ttk.Button(self.exportModToolbarFrame, text="Pack Mod", command = lambda: self.pack())
        self.RemoveAllPackFilesButton = ttk.Button(self.exportModToolbarFrame, text="Remove All", command = lambda: self.RemoveAllPackFiles())

        self.exportModCreateNew.grid(row=0, column=0, sticky="nsew")
        self.exportModExport.grid(row=0, column=1, sticky="nsew")
        self.RemoveAllPackFilesButton.grid(row=0, column=2, sticky="nsew")

        self.exportModToolbarFrame.grid_columnconfigure(0, weight=0, uniform="button")
        self.exportModToolbarFrame.grid_columnconfigure(2, weight=0, uniform="button")
        self.exportModToolbarFrame.grid_rowconfigure(0, weight=1)
        self.packModFrame.grid_rowconfigure(2, weight=0, minsize=45)

        self.tabs.bind("<<NotebookTabChanged>>", lambda event:self.mainWindow.focus_set())

        for widget in self.manageModsFrame.winfo_children():

            widget.bind("<1>", lambda event:self.mainWindow.focus_set())
           
        for widget in self.exportModCanvasFrame.winfo_children():

            if widget.winfo_class() == "Entry":

                widget.bind("<1>", lambda event:widget.focus_set())
           
        self.config()

        try:
            mkdir(self.planetCoasterDir + "/backups/")
        except:
            pass

        self.mainWindow.mainloop()

    def createNewExportFile(self):

        if not hasattr(self, 'exportFileList'):

            self.exportFileList = []

        fileDir = askopenfilenames()
        ovlDir = ""

        for file in fileDir:
            self.exportFileList.append(PackFileWidget(self, self.exportModCanvasFrame.scrollable_frame, len(self.exportFileList), 0, ovlDir, file))
            self.exportFileList[-1].entryVar.set(ovlDir)

    def RemoveAllPackFiles(self):
        for item in self.exportFileList:
            print(item.file)
            item.destroy()

    def styles(self):

        self.style = ttk.Style(self.mainWindow)
        self.headerFont = font.Font(size=20, weight='bold')

    def config(self):

        self.config = configparser.ConfigParser()
        self.config.read("Data/config.ini")

        self.planetCoasterDir = self.config["DEFAULT"]["GameDirectory"]


        if self.config["DEFAULT"]["HasSetup"] != "True" or not path.isdir(self.config["DEFAULT"]["GameDirectory"]):

            self.planetCoasterDir = messagebox.showinfo("Welcome!", "Please select your Planet Coaster installation folder (usually found in the Steamgames folder)") 

            while True:

                self.planetCoasterDir = askdirectory()

                if self.planetCoasterDir.split("/")[-1] != "Planet Coaster":

                    messagebox.showerror("Error", "Not a valid Planet Coaster directory!")

                else:
                    break

            self.config["DEFAULT"] = {
                "GameDirectory": self.planetCoasterDir, "HasSetup": True}
            
            with open("Data/config.ini", "w") as configfile:
                self.config.write(configfile)

        self.version = self.config["DEFAULT"]["version"]
        try:
            self.updater = Updater()
            if self.updater.check_update(self.version):
                print("updating...")
                messagebox.showinfo("Updater", "Update Required To Version {}".format(self.updater.get_tag()))
                self.updater.update()


            self.config["DEFAULT"]["version"] = self.updater.get_tag()
            with open("Data/config.ini", "w") as configfile:
                self.config.write(configfile)
        except:
            messagebox.showinfo("Updater Broke", "Updater could not ping github server so cannot check for update")

    def pack(self):

        self.modName = (self.metaNameEntry.get()).strip()
        self.metaAuth = (self.metaAuthEntry.get()).strip()
        self.metaDesc = (self.metaDescEntry.get()).strip()

        self.Meta = pcm.meta(self.modName ,self.metaAuth,self.metaDesc)

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
            mkdir(self.saveDir)
        except:
            pass
        self.Meta = pcm.meta(self.metaNameEntry.get() ,self.metaAuthEntry.get(),self.metaDescEntry.get())
        self.PCM = pcm.pcm(self.out, self.Meta)
        self.PCM.write_meta()
        self.PCM.write_pcm()
        self.PCM.pcm_write_to_file(self.saveDir)

        for self.test in self.temp:
            self.shortenedOVLPath = self.shortenedOVLPath[self.shortenedOVLPath.find("Win64"):]
            self.dirName = self.shortenedOVLPath.replace("/","_")
            self.dirName = self.dirName.replace(":","#")
            print(self.saveDir + "/" + self.dirName)
            try:
                mkdir(self.saveDir + "/" + self.dirName)
            except:
                pass
            shutil.copyfile(self.test.file, self.saveDir + "/" + self.dirName + "/" +self.test.file.split("/")[-1])

        shutil.make_archive(self.saveDir, 'zip', self.saveDir)
        rename(self.saveDir + ".zip", self.saveDir + ".pcm")
        shutil.rmtree(self.saveDir)

    def inject_mod(self, filepath):
        self.modToBeInjected = Mod(self)
        #self.modList = self.loadModsList()
        self.modToBeInjected.loadMeta(filepath)
            
        if (any(x.modName == self.modToBeInjected.modName for x in self.modList)) == False:
            self.modToBeInjected.install(filepath)
            self.modToBeInjected.save()
            self.modList.append(self.modToBeInjected)
            widget = ModTileWidget(self.modToBeInjected, self, self.manageModsScrollFrame.scrollable_frame, self.modList.index(self.modToBeInjected), 0)
            self.modWidgetList.append(widget)

        else:
            messagebox.showinfo("Information", "Mod with this name is already installed, try remove any mods with the same name!") #Add in option to continue?

    def restore(self):
        for i in range(len(self.modWidgetList)):
            self.modWidgetList[i].destroy()
            #self.modWidgetList[i].modFile.uninstall()

    def loadModsList(self):
        self.tempList = []
        with open("Data/mods.json", "r") as file:
            self.fileData = file.read()
            if len(self.fileData) == 0:
                return self.tempList
            self.modData = loads(self.fileData)
            for self.mod in self.modData:
                self.newMod = Mod(self)
                self.newMod.modName = self.modData[self.mod]["Name"]
                self.newMod.modAuthor = self.modData[self.mod]["Author"]
                self.newMod.modDesc = self.modData[self.mod]["Desc"]
                self.newMod.backupPaths = self.modData[self.mod]["Backups"]
                self.newMod.OVLs = self.modData[self.mod]["OVLs"]
                self.tempList.append(self.newMod)
        return self.tempList

class PackFileWidget():

    def __init__(self, gui, parent, row, column, ovlFile, file):

        self.gui = gui
        self.file = file
        self.ovlFile = ovlFile
        self.frame = ttk.Frame(parent, borderwidth = 4, height=5)

        self.dirFrame = ttk.Frame(self.frame)

        self.frame.grid_columnconfigure(0, weight=0, uniform="title", minsize=135)
        self.frame.grid_columnconfigure(1, weight=1, uniform="dir")

        self.directoryLabel = ttk.Label(self.frame, text = file.split("/")[-1], font = font.Font(size=14, weight="bold"))

        self.entryVar = tk.StringVar()

        self.entryLabel = ttk.Entry(self.dirFrame, exportselection=0, textvariable=self.entryVar)
        self.entryLabel.bind("<1>", lambda event:self.entryLabel.focus_set())

        self.entryLabel.focus_set()
        self.entryLabel.insert(index = 0, string = "Enter targeted OVL path")

        self.ovlDirButton = ttk.Button(self.dirFrame, text="Quickfill Dir", command=lambda: self.entryVar.set(self.setAndTruncateDir()))

        self.destroyButton = ttk.Button(self.frame, text="×", command=lambda: self.destroy())

        self.frame.grid(row=row, column=column, sticky="nsew")
        self.directoryLabel.grid(row=0, column=0, sticky="nsw")
        self.destroyButton.grid(row=0, column=1, sticky="nse")

        self.destroyButton.configure(width=self.destroyButton.winfo_height() * 2)

        self.dirFrame.grid(row=1, column=0, columnspan=2, sticky="nsew")

        self.dirFrame.grid_columnconfigure(0, weight=1, uniform="dir")
        self.dirFrame.grid_columnconfigure(1, weight=0, uniform="selfFill", minsize=135)

        self.entryLabel.grid(row=2, column=0, sticky="nsew")
        self.ovlDirButton.grid(row = 2, column=1, sticky="nsew")

    def destroy(self):

        self.frame.destroy()
        self.gui.exportFileList.pop(self.gui.exportFileList.index(self))

    def setAndTruncateDir(self):

        ovlDir = askopenfilename(filetypes=[("Archive File","*.ovl")], initialdir=self.gui.planetCoasterDir+"/Win64/ovldata")

        if ovlDir != "":

            if self.gui.planetCoasterDir in ovlDir:

                dir = ovlDir.replace(self.gui.planetCoasterDir, "")
            
                if dir.split(".")[-1] != "ovl":

                    messagebox.showerror("Error", "Not an OVL file!")
                    return self.entryVar.get()

                else:

                    return dir 

            else:

                messagebox.showerror("Error", "Not a valid Planet Coaster directory!")
                return self.entryVar.get()

        else:

            return self.entryVar.get()

class ModTileWidget():

    def __init__(self, modfile, gui, parent, row, column):


        self.gui = gui

        self.modFile = modfile

        self.modName = modfile.modName
        self.modDesc = modfile.modDesc
        self.modAuthor = modfile.modAuthor

        self.containerFrame = ttk.Frame(parent, borderwidth=4)
        self.metaFrame = ttk.Frame(self.containerFrame, borderwidth=0)

        self.nameLabel = ttk.Label(self.containerFrame, text=self.modName, font = font.Font(size=14, weight="bold"))
        self.descLabel = ttk.Label(self.metaFrame, text=self.modDesc, justify="left", anchor = "nw")
        self.authLabel = ttk.Label(self.metaFrame, text="By: " + self.modAuthor, font = font.Font(size=10, weight="bold"))

        self.spacer = ttk.Separator(self.metaFrame)

        self.nameLabel.grid(row=0, column=0, sticky="nsew")
        self.descLabel.grid(row=0, column=0, sticky="nsew")
        self.spacer.grid(row=1, column=0, sticky="sew")
        self.authLabel.grid(row=2, column=0, sticky="sew")

        self.metaFrame.grid_columnconfigure(0, weight=1)
        self.metaFrame.grid_rowconfigure(0, weight=1)

        self.containerFrame.grid_columnconfigure(0, weight=1)

        self.destroyButton = ttk.Button(self.containerFrame, text="×", command=lambda: self.destroy())

        self.destroyButton.grid(row=0, column=1, sticky="nw")

        self.destroyButton.configure(width=self.destroyButton.winfo_height() * 2)

        def reTextWrap(evt):

            self.descLabel.configure(wraplength=self.containerFrame.winfo_width() - 8)

        self.containerFrame.bind("<Configure>", reTextWrap)

        self.containerFrame.grid(row=row, column=column, sticky="nsew")
        self.metaFrame.grid(row=1, column=0, columnspan=2, sticky="nsew")

    def destroy(self):
        print(self.modFile.modName + " should be uninstalled")
        if self.modFile in self.gui.modList:
            self.containerFrame.destroy()
            self.modFile.uninstall()



## Taken from 
## https://blog.tecladocode.com/tkinter-scrollable-frames/

class ScrollableFrame(ttk.Frame):
    def __init__(self, container, gui, *args, **kwargs):
        super().__init__(container, *args, **kwargs)

        print(gui.style.element_options("Frame.border"))

        self.canvas = tk.Canvas(self, bg=gui.style.lookup("TFrame", "background"), highlightcolor=gui.style.lookup("TFrame", "darkcolor"), highlightbackground=gui.style.lookup("TFrame", "darkcolor"))
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas, borderwidth=0)

        self.scrollable_frame.grid_columnconfigure(0, weight=1)

        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        self.canvasWindow = self.canvas.create_window((4, 4), window=self.scrollable_frame, anchor="nw")

        def resize(evt):

            self.canvas.itemconfig(self.canvasWindow, width = self.canvas.winfo_width() - 4)


        self.canvas.bind("<Configure>", resize)


        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")



gui = Gui()

        
