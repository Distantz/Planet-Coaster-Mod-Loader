# IMPORTANT
As of **07/08/2024**, this repository is now private. Better things are coming for Planet Coaster modding, and this program is now outdated.

# Planet Coaster Mod Loader
This program installs and packs Planet Coaster mods (.pcm files).

## How to use
The Planet Coaster Mod Loader was designed to be as intuitive as possible, so everything should be relatively self-explanitory.

### Installing and removing mods
Mods are installed using the install mods button on the Manage tab. When these mods are loaded into the manager, it may take a while for the application to respond to user input, as it is injecting the mod into the gamefiles.

Removing a mod can be done in one of two ways, either click the mods delete button in the Mod Management interface, or uninstall all mods in the Mod Manager. Note that uninstalling a mod removes all mod functionality using that specific OVL.

### Packing modified gamefiles into a mod file

#### Adding files
Mods are incredibly easy to make, simply navigate to the Export tab and click the Add new file button at the bottom of the interface. Add the files you want to change in your mod and then put the relative filepath of the OVL file you're modifying into the text entry (clicking the Autofill Dir button will allow you to pick the ovl file in the game directory and auto-fill the text entry).

#### Adding metadata
Mods can have a name, description and authors added to them, for easier sorting in the Mod Manager. Try to keep the name short, but the description can be as long as you please. Recommended formatting for the author metadata is as follows; Name, Name and Name (will be displayed as By: Name, Name and Name)

#### Exporting
Once finished, the mod can be exported by clicking the Pack button at the bottom of the interface, this will prompt you to pick a location for the program to output a "modname".pcm file. This can then be installed into your mod manager and other peoples mod managers.

## Credits

### Developers
* Evan
* Thomas (Distantz)

### Testers
* Silentmember
* iDro

### Derivatives 
* Injecting game files: https://github.com/OpenNaja/cobra-tools
* Scrollable Frames based off: https://blog.tecladocode.com/tkinter-scrollable-frames
* Themed gui: https://sourceforge.net/projects/tcl-awthemes/
