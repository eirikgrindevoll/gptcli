
# GPTCLI: Autonomous Command Line Interface Powered by GPT-4

GPTCLI is an innovative autonomous tool that integrates OpenAI's GPT-4 model with a command-line interface. Currently tested on Linux Ubuntu WSL, it leverages the GPT-4 model to provide an interactive environment where the system autonomously derives and executes appropriate commands based on the provided context or task.

## Features

- **Autonomous Interactions**: Works autonomously without requiring user interaction after the initial task is inputted.
- **Natural Language Processing**: Leverages OpenAI's GPT-4 model to interpret the context and generate relevant commands.
  
![demo](https://github.com/eirikgrindevoll/gptcli/assets/43350451/3a20bef7-496f-4e21-8a62-06650c7a4ebd)

## Usage

After setting up the OpenAI API key in the `gptcli.conf` file, you can run the script and provide the task or context. GPTCLI will autonomously generate and execute the appropriate commands. 

## Purpose

The aim of this project is to provide a tool that can perform tasks based on natural language inputs


## System Requirements

GPTCLI is designed to run on platforms with Python 3.x and the OpenAI Python client. 

pip install -r requirements.txt

**Note:** As this tool can autonomously execute commands on your system, please use it responsibly and be aware of the potential security implications.
