import openai
import subprocess
import re
import pexpect
import sys
import io
import json
import os
import distro
import platform
import json
import os
import atexit
import backoff
import configparser
from functools import partial
from getpass import getpass

from colorama import init as colorama_init
from colorama import Fore
from colorama import Style

colorama_init()

config = configparser.ConfigParser()
config.read('gptcli.conf')
openai.api_key = config.get('OpenAI', 'api_key')

if not openai.api_key:
    raise ValueError("Missing OpenAI API key. Check your configuration file")

@backoff.on_exception(
    backoff.expo,
    (openai.error.RateLimitError, openai.error.ServiceUnavailableError),
    max_tries=10,
    max_value=60  
)
def run_gpt_prompt(conversation_history, log_file="gpt_log.txt"):

    user_input = conversation_history[-1]["content"]

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=conversation_history,
        temperature=0.6,
    )

    response_text = response.choices[0].message["content"].strip()

    # Log the conversation history
    with open(log_file, "a") as log:
        log.write(json.dumps(conversation_history[-2:], ensure_ascii=False, indent=2))
        log.write("\n\n")

    return response_text

	
def extract_commands(ai_response):
    command_pattern = r'\[\[execute:(.+?)\]\]'
    commands = re.findall(command_pattern, ai_response, re.DOTALL)
    return [command.strip() for command in commands]

def remove_ansi_escape_codes(text):
    ansi_escape_pattern = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape_pattern.sub('', text)

def execute_command(command, timeout=300, sudo_password=None):
    try:
        if command.startswith("sudo"):
            child = pexpect.spawnu(command, timeout=timeout, logfile=None)

            child.expect("password for .*:")
            child.sendline(sudo_password)

            child.logfile = sys.stdout # can be removed if GPT will show the results back
            patterns = [pexpect.EOF, r"Do you want to continue\? \[Y\/n\]", r"(?i)lines(.*)"]
            while True:
                index = child.expect(patterns)

                if index == 1:  # y/n prompt detected
                    user_input = input("Do you want to continue? [Y/n]: ")
                    child.sendline(user_input)
                elif index == 2:  # pager output detected
                    output = child.before.strip()
                    child.sendline("q")
                else:
                    break


            output = (output if 'output' in locals() else child.before.strip())
 
            if child.isalive() or child.exitstatus != 0:
                return f"Error: {remove_ansi_escape_codes(output)}"
            else:
                return f"Command successfully executed: {remove_ansi_escape_codes(output)}"
			
        else:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                return f"Error: {stderr.strip()}"

        return f"Command successfully executed {stdout.strip()}"
		
       

    except pexpect.TIMEOUT:
        return "Error: Command execution timed out (pexpect)."
    except Exception as e:
        return str(e)


    
def save_history(conversation_history):
    with open("conversation_history.json", "w") as outfile:
        json.dump(conversation_history, outfile, indent=4)

def main():

    
    print("GPT Linux Command Line Integration")
    print("Type 'quit' to exit the program")

   
    platform_system = platform.system()
    platform_release = platform.release()
    platform_architecture = platform.architecture()
    distribution_name = distro.name(pretty=True)
	
    system_message = (
    f"You are a autonomous agent that can interact with your environment. "
    f"You have the ability to execute commands on this system and access the internet to gather information. "
    f"Your responses should strictly adhere to this format: [[execute:YOUR_COMMAND_HERE]], replacing YOUR_COMMAND_HERE with the actual command. "
    f"Do not include any explanations, instructions, additional spaces or newline characters in your response. "
    f"Do not suggest or recommend any interactive commands, such as using 'nano' to edit files. "
    f"Instead, use non-interactive commands to perform tasks like writing to a file. "
    f"However, you can provide feedback about the state of the system or ask for user input in natural language, outside of the [[execute:YOUR_COMMAND_HERE]] format. "
    f"Seek necessary user input without directing them to perform any actions. The input should be relevant to completing a command, and avoid suggesting example data. "
    f"Do not suggest code or commands in other formats then [[execute:YOUR_COMMAND_HERE]]. "
    f"If a command requires a tool that is not available, you can install the tool, "
    f"and the user will handle the elevation of privileges if the sudo is included in the command. "
    f"Do not provide the example format to the user. Just ask the user for the task you should execute."
    f"Do not use system variables or non-specific commands in your responses. If any additional information or specific parameters are required for a command, ask the user for it. "
    f"System information: \n"
    f"Platform System: {platform_system}\n"
    f"Platform Release: {platform_release}\n"
    f"Platform Architecture: {platform_architecture}\n"
    f"Distribution Name: {distribution_name}"
    )
  
    conversation_history = [
        {
            "role": "system",
            "content": system_message
        }
    ]

    atexit.register(partial(save_history, conversation_history))

   # conversation_history.append({"role": "user", "content": system_message})

    sudo_password = None


    while True:
        user_input = input("Enter your task: ")

        if user_input.lower() == "quit":
            save_history(conversation_history)
            break

        gpt_input = user_input

		
        reinforced_input = (
            f"'{user_input}' \n"
            "Respond with step-by-step actions, "
            "in the exact format specified in the system prompt, with no explanation.\n"
            "If needing to use echo and sudo then use single quotes for echo and pipe to sudo tee filename. Use -qq and -y with apt. Always use the most secure and latest technology."
        )

        conversation_history.append({"role": "user", "content": reinforced_input})

        gpt_output = run_gpt_prompt(conversation_history)
        conversation_history.append({"role": "assistant", "content": gpt_output})
        #print(gpt_output) #Show all
        commands = extract_commands(gpt_output)

        if not commands:
            print("No commands found in GPT output.")
            print(Fore.YELLOW + gpt_output + Style.RESET_ALL )
        else:
            
            idx = 0
            while idx < len(commands):
                command = commands[idx]
                #print(Fore.RED + "Executing command:" + command  + Style.RESET_ALL)

                if command.startswith("sudo") and sudo_password is None:
                    sudo_password = getpass("Enter your sudo password: ")

                result = execute_command(command, sudo_password=sudo_password) if sudo_password else execute_command(command)
                
                if result.startswith ("Command successfully executed") :
                   print(Fore.GREEN + result + Style.RESET_ALL )
				   
               

                # Send the command output back to GPT for further processing
                # Check if there is a next command
                has_next_command = idx + 1 < len(commands)
                if has_next_command:
                    next_command = f"This is the next command that will be executed: {commands[idx + 1]}"
                else:
                    next_command = "If the task is complete summarize the task performed in natural language otherwise provide the next command"
                
            
                conversation_history.append({"role": "user", "content": f"Result:{result}. Avoid repeating commands unless correcting. {next_command} "})
                gpt_output = run_gpt_prompt(conversation_history)
                conversation_history.append({"role": "assistant", "content": gpt_output})
                #print(gpt_output)
                if '[[stopexecuting]]' in gpt_output.lower():
                    print("Aborting command execution as per GPT's instruction.")
                    break
                # Extract commands from GPT output and replace the commands list
                new_commands = extract_commands(gpt_output)
                if new_commands:
                    
                    commands = new_commands

                    # Reset the loop index to the start of the new commands list
                    idx = 0
                else:
                    # Increment the loop index only if there are no new commands
                    print(Fore.YELLOW + gpt_output + Style.RESET_ALL )
                    idx += 1
   
if __name__ == "__main__":
    main()
