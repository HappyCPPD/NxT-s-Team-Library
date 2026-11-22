# **Game Boy CTF Challenge: my\_first\_chall**

This repository contains the source code for a simple reverse engineering CTF challenge designed for the original Nintendo Game Boy. The goal is to analyze the provided Game Boy ROM, discover a secret button sequence, and enter it to reveal the flag.

## **Challenge Overview**

An old game console is keeping a secret. The program asks for an 8-part code to be entered using the Game Boy's controller. If the correct sequence of buttons is pressed, the program will decrypt and display the hidden flag. The challenge is to reverse engineer the program logic to find this sequence.

* **Category:** REV 
* **Difficulty:** Medium 
* **Author:** [Pratyush-gg](https://github.com/Pratyush-gg)

## **How to Compile**

To compile the main.c source code into a Game Boy ROM (.gb file), you need to have the **Game Boy Development Kit (GBDK)** installed and configured.

### **1\. GBDK Setup**

* **Windows:** The easiest way to get started is with the gbdk-2020 installer package, which can be found on GitHub. Download and run the installer, which will set up the compiler and add it to your system's PATH. 
* **macOS/Linux:** You will need to clone the gbdk-2020 repository and build it from the source. Follow the instructions provided in the GBDK documentation.

### **2\. Compilation Command**

Once GBDK is installed, navigate to the project directory in your terminal and run the following command to compile main.c into sauce.gb:

lcc \-o sauce.gb main.c

## **How to Play**

You will need a Game Boy emulator to run the sauce.gb file.

1. Compile the source code using the command above. 
2. Open the resulting sauce.gb file in a Game Boy emulator of your choice (see recommendations below). 
3. The screen will prompt you to "Enter the 8-part code\!". 
4. Use the emulator's controls to input the button sequence you discovered during your analysis.

## **Recommended Tools**

* **Emulator (BGB):** For this challenge, the **BGB emulator** is highly recommended. It is a very accurate Game Boy emulator that includes a powerful, user-friendly debugger. 
* **Reverse Engineering:** A disassembler/decompiler is essential for analyzing the ROM. **IDA Pro** or **Ghidra** are excellent free tools that support the Game Boy's processor architecture.
## **Solution**

### **Step 1: Dynamic Analysis**

The first step is to understand the program's behavior by running it in an emulator. For this, BGB is an excellent choice due to its debugging capabilities.

* **Load the ROM:** Open sauce.gb in BGB or another Game Boy emulator. 
* **Observe the Program:** The screen displays "Welcome to CTF\!" and "Enter the 8-part code\!". Below this, there is a prompt: Code: \[........\]. 
* **Interact with the Program:** Pressing buttons on the D-pad or the A/B buttons causes an asterisk \* to appear over the dots, one for each press. After eight presses, the program either displays "Wrong Code\! Try again." and resets, or it reveals the flag.

From this initial analysis, we can conclude:

* The goal is to find a specific sequence of 8 button presses. 
* The program checks the entire sequence at once after the 8th input.

### **Step 2: Static Analysis with IDA Pro**

Since guessing the sequence is not feasible, we need to analyze the program's code. We will use IDA Pro for this.

* **Examine the Code:** Inside the main function, we can clearly see the logic: 
 * An array named secret\_sequence is defined. 
 * The program enters a while(1) loop to handle input. 
 * It reads joypad input and stores each of the first 8 presses into an input\_buffer. 
 * After 8 inputs, it uses memcmp to compare the input\_buffer with the hardcoded secret\_sequence. 
 * If the comparison is successful, it decrypts and shows the flag.

### **Step 3: Extracting the Secret Sequence**

The key to the challenge is the secret\_sequence array found in the code.

UINT8 secret\_sequence\[8\] \= {J\_UP, J\_DOWN, J\_UP, J\_DOWN, J\_B, J\_A, J\_B, J\_A};

* **Translate the Values:** We need to map these byte values to the actual Game Boy buttons. By consulting GBDK's documentation or using BGB's debugger, we find the mapping: 
 * J\_UP: 0x04 
 * J\_DOWN: 0x08 
 * J\_LEFT: 0x02 
 * J\_RIGHT: 0x01 
 * J\_A: 0x10 
 * J\_B: 0x20 
 * J\_START: 0x80 
 * J\_SELECT: 0x40

The sequence in memory is \[0x04, 0x08, 0x04, 0x08, 0x20, 0x10, 0x20, 0x10\].

* Determine the Final Code: Translating these values gives us the final sequence: 
 UP, DOWN, UP, DOWN, B, A, B, A

### **Step 4: Unlocking the Flag**

* **Return to the Emulator:** Go back to the BGB emulator running the ROM. 
* **Enter the Sequence:** Carefully press the buttons in the correct order: UP, DOWN, UP, DOWN, B, A, B, A.

### **The Flag**

The revealed flag is: 
d4rk{1\_l0v3\_G4m3y}c0de 
