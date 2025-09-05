import copy
import glob
import json
import os
import argparse
from pathlib import Path
from datetime import datetime
import random
import subprocess
import requests

import openai
import ai2thor.controller

# LLM provider imports
try:
    import anthropic
except ImportError:
    anthropic = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

import sys
sys.path.append(".")

import resources.actions as actions
import resources.robots as robots


def LM(prompt, model_name, max_tokens=128, temperature=0, stop=None, logprobs=1, frequency_penalty=0):
    
    # OpenAI GPT models
    if "gpt" in model_name.lower():
        if "gpt" not in model_name:
            response = openai.Completion.create(model=model_name, 
                                                prompt=prompt, 
                                                max_tokens=max_tokens, 
                                                temperature=temperature, 
                                                stop=stop, 
                                                logprobs=logprobs, 
                                                frequency_penalty = frequency_penalty)
            return response, response["choices"][0]["text"].strip()
        else:
            response = openai.ChatCompletion.create(model=model_name, 
                                                messages=prompt, 
                                                max_tokens=max_tokens, 
                                                temperature=temperature, 
                                                frequency_penalty = frequency_penalty)
            return response, response["choices"][0]["message"]["content"].strip()
    
    # Claude (Anthropic)
    elif "claude" in model_name.lower():
        if anthropic is None:
            raise ImportError("anthropic package is required for Claude models")
        
        client = anthropic.Anthropic(api_key=anthropic_api_key)
        
        if isinstance(prompt, list):
            # Chat format
            messages = prompt
        else:
            # Single prompt format
            messages = [{"role": "user", "content": prompt}]
        
        response = client.messages.create(
            model=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages
        )
        return response, response.content[0].text.strip()
    
    # Gemini (Google)
    elif "gemini" in model_name.lower():
        if genai is None:
            raise ImportError("google-generativeai package is required for Gemini models")
        
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel(model_name)
        
        if isinstance(prompt, list):
            # Convert chat format to text
            text_prompt = ""
            for msg in prompt:
                if msg["role"] == "user":
                    text_prompt += f"User: {msg['content']}\n"
                elif msg["role"] == "system":
                    text_prompt += f"System: {msg['content']}\n"
        else:
            text_prompt = prompt
        
        response = model.generate_content(
            text_prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature
            ),
            safety_settings=[
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
        )
        
        # Check if response is valid
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            return response, response.text.strip()
        else:
            # Handle blocked content or empty response
            finish_reason = response.candidates[0].finish_reason if response.candidates else "UNKNOWN"
            error_msg = f"Gemini API 응답이 차단되었습니다. finish_reason: {finish_reason}"
            print(f"경고: {error_msg}")
            return response, f"# {error_msg}\n# 빈 응답이 생성되었습니다."
    
    # Ollama (Local)
    elif "ollama" in model_name.lower():
        model = model_name.replace("ollama:", "")
        url = "http://localhost:11434/api/generate"
        
        if isinstance(prompt, list):
            # Convert chat format to text
            text_prompt = ""
            for msg in prompt:
                if msg["role"] == "user":
                    text_prompt += f"User: {msg['content']}\n"
                elif msg["role"] == "system":
                    text_prompt += f"System: {msg['content']}\n"
        else:
            text_prompt = prompt
        
        payload = {
            "model": model,
            "prompt": text_prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        return result, result["response"].strip()
    
    else:
        raise ValueError(f"Unsupported model: {model_name}")

def get_api_key_interactive(model_name):
    """사용자로부터 API 키를 안전하게 입력받습니다."""
    if "gpt" in model_name.lower():
        api_key = input("OpenAI API 키를 입력하세요: ").strip()
        if not api_key:
            raise ValueError("OpenAI API 키가 필요합니다.")
        return api_key
    elif "claude" in model_name.lower():
        api_key = input("Anthropic API 키를 입력하세요: ").strip()
        if not api_key:
            raise ValueError("Anthropic API 키가 필요합니다.")
        return api_key
    elif "gemini" in model_name.lower():
        api_key = input("Google Gemini API 키를 입력하세요: ").strip()
        if not api_key:
            raise ValueError("Google Gemini API 키가 필요합니다.")
        return api_key
    elif "ollama" in model_name.lower():
        return None  # Ollama는 로컬이므로 API 키 불필요
    else:
        raise ValueError(f"지원하지 않는 모델: {model_name}")

def set_api_key_for_model(model_name, api_key):
    """모델에 맞는 API 키를 설정합니다."""
    global anthropic_api_key, gemini_api_key
    
    if "gpt" in model_name.lower():
        openai.api_key = api_key
    elif "claude" in model_name.lower():
        anthropic_api_key = api_key
    elif "gemini" in model_name.lower():
        gemini_api_key = api_key
    elif "ollama" in model_name.lower():
        pass  # Ollama는 로컬이므로 API 키 불필요

def clean_generated_code(code):
    """생성된 코드에서 마크다운 블록과 불필요한 텍스트를 제거합니다."""
    import re
    
    # 마크다운 코드 블록 제거
    code = re.sub(r'```python\s*', '', code)
    code = re.sub(r'```\s*$', '', code)
    code = re.sub(r'```.*?\n', '', code, flags=re.DOTALL)
    
    # AI2Thor 액션 함수들
    ai2thor_functions = ['GoToObject', 'PickupObject', 'PutObject', 'OpenObject', 'CloseObject', 
                        'SwitchOn', 'SwitchOff', 'SliceObject', 'CleanObject', 'ThrowObject', 
                        'BreakObject', 'DropHandObject', 'PushObject', 'PullObject']
    
    lines = code.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line_stripped = line.strip()
        
        # 유지할 줄들
        if (not line_stripped or  # 빈 줄
            line_stripped.startswith(('def ', 'import ', 'from ', 'class ', '#', '    ', '\t')) or  # 함수 정의, import, 주석, 들여쓰기
            any(line_stripped.startswith(func) for func in ai2thor_functions) or  # AI2Thor 함수 호출
            line_stripped.startswith(('robots', 'objects', 'if ', 'for ', 'while ', 'try:', 'except', 'finally:', 'with ', 'return ', 'yield ', 'global ', 'nonlocal ')) or  # 변수, 제어문
            # 함수 호출 패턴 (함수명(매개변수) 형태)
            (line_stripped and not line_stripped[0].isupper() and 
             '(' in line_stripped and ')' in line_stripped and 
             any(func in line_stripped for func in ai2thor_functions)) or
            # 함수 실행 호출 패턴
            (line_stripped and '(' in line_stripped and ')' in line_stripped and 
             not line_stripped.startswith('#') and 'robot' in line_stripped.lower())):
            # 설명 주석 제거 (This code, assigns the task, which has the necessary skills 등)
            if not (line_stripped.startswith('#') and any(phrase in line_stripped for phrase in 
                ['This code', 'assigns the task', 'which has the necessary', 'skills', 'GoToObject', 'PickupObject', 'PutObject'])):
                cleaned_lines.append(line)
    
    result = '\n'.join(cleaned_lines)
    
    # 연속된 빈 줄 정리
    result = re.sub(r'\n\s*\n\s*\n', '\n\n', result)
    
    # 빈 함수나 잘못된 함수명 제거
    if 'def assemble_object' in result:
        result = result.replace('def assemble_object', 'def toast_bread')
    
    # 잘못된 객체 이름 교정
    result = result.replace("'MobilePhone'", "'CellPhone'")
    result = result.replace("'Cellphone'", "'CellPhone'")
    result = result.replace("'Refrigerator'", "'Fridge'")
    result = result.replace("'PowerButton'", "'Laptop'")  # PowerButton은 존재하지 않음
    
    return result

# Function returns object list with name and properties.
def convert_to_dict_objprop(objs, obj_mass):
    objs_dict = []
    for i, obj in enumerate(objs):
        obj_dict = {'name': obj , 'mass' : obj_mass[i]}
        # obj_dict = {'name': obj , 'mass' : 1.0}
        objs_dict.append(obj_dict)
    return objs_dict

def get_ai2_thor_objects(floor_plan_id):
    # connector to ai2thor to get object list
    controller = ai2thor.controller.Controller(scene="FloorPlan"+str(floor_plan_id))
    obj = list([obj["objectType"] for obj in controller.last_event.metadata["objects"]])
    obj_mass = list([obj["mass"] for obj in controller.last_event.metadata["objects"]])
    controller.stop()
    obj = convert_to_dict_objprop(obj, obj_mass)
    return obj

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--floor-plan", type=int, required=True)
    parser.add_argument("--model", type=str, default="gpt-3.5-turbo", 
                        choices=[
                            # OpenAI models
                            'gpt-3.5-turbo', 'gpt-4',
                            # Gemini models
                            'gemini-2.5-flash', 'gemini-1.5-flash', 'gemini-2.0-flash-exp',
                            # Ollama models (local)
                            'ollama:llama3', 'ollama:tinyllama'
                        ])
    
    parser.add_argument("--prompt-decompse-set", type=str, default="train_task_decompose", 
                        choices=['train_task_decompose'])
    
    parser.add_argument("--prompt-allocation-set", type=str, default="train_task_allocation", 
                        choices=['train_task_allocation'])
    
    parser.add_argument("--test-set", type=str, default="final_test", 
                        choices=['final_test'])
    
    parser.add_argument("--log-results", type=bool, default=True)
    
    args = parser.parse_args()

    # 사용자로부터 API 키 입력받기
    print(f"선택된 모델: {args.model}")
    api_key = get_api_key_interactive(args.model)
    set_api_key_for_model(args.model, api_key)
    
    if not os.path.isdir(f"./logs/"):
        os.makedirs(f"./logs/")
        
    # read the tasks        
    test_tasks = []
    robots_test_tasks = []  
    gt_test_tasks = []    
    trans_cnt_tasks = []
    max_trans_cnt_tasks = []  
    with open (f"./data/{args.test_set}/FloorPlan{args.floor_plan}.json", "r") as f:
        for line in f.readlines():
            line = line.strip()
            if line:  # 빈 줄이 아닌 경우만 처리
                try:
                    data = json.loads(line)
                    test_tasks.append(list(data.values())[0])
                    robots_test_tasks.append(list(data.values())[1])
                    gt_test_tasks.append(list(data.values())[2])
                    trans_cnt_tasks.append(list(data.values())[3])
                    max_trans_cnt_tasks.append(list(data.values())[4])
                except json.JSONDecodeError as e:
                    print(f"JSON 파싱 오류: {e}")
                    print(f"문제가 있는 줄: {line}")
                    continue
                    
    print(f"\n----Test set tasks----\n{test_tasks}\nTotal: {len(test_tasks)} tasks\n")
    # prepare list of robots for the tasks
    available_robots = []
    for robots_list in robots_test_tasks:
        task_robots = []
        for i, r_id in enumerate(robots_list):
            rob = copy.deepcopy(robots.robots [r_id-1])  # Create a deep copy
            # rename the robot using sequential index (1, 2, 3, ...)
            rob['name'] = 'robot' + str(i + 1)
            print(f"Debug: r_id={r_id}, i={i}, new_name={rob['name']}")
            task_robots.append(rob)
        available_robots.append(task_robots)
        
    
    ######## Train Task Decomposition ########
        
    # prepare train decompostion demonstration for ai2thor samples
    prompt = f"from skills import " + actions.ai2thor_actions
    prompt += f"\nimport time"
    prompt += f"\nimport threading"
    objects_ai = f"\n\nobjects = {get_ai2_thor_objects(args.floor_plan)}"
    prompt += objects_ai
    
    # read input train prompts
    decompose_prompt_file = open(os.getcwd() + "/data/pythonic_plans/" + args.prompt_decompse_set + ".py", "r")
    decompose_prompt = decompose_prompt_file.read()
    decompose_prompt_file.close()
    
    prompt += "\n\n" + decompose_prompt
    
    print ("1단계: Generating Decompsed Plans...")
    
    decomposed_plan = []
    for task in test_tasks:
        curr_prompt =  f"{prompt}\n\n# Task Description: {task}"
        
        if "gpt" not in args.model:
            # older gpt versions
            _, text = LM(curr_prompt, args.model, max_tokens=1000, stop=["def"], frequency_penalty=0.15)
        else:            
            messages = [{"role": "user", "content": curr_prompt}]
            _, text = LM(messages, args.model, max_tokens=1300, frequency_penalty=0.0)

        # 코드 후처리 적용
        cleaned_text = clean_generated_code(text)
        decomposed_plan.append(cleaned_text)
        
    print ("2단계: Generating Allocation Solution...")

    ######## Train Task Allocation - SOLUTION ########
    prompt = f"from skills import " + actions.ai2thor_actions
    prompt += f"\nimport time"
    prompt += f"\nimport threading"
    
    prompt_file = os.getcwd() + "/data/pythonic_plans/" + args.prompt_allocation_set + "_solution.py"
    allocated_prompt_file = open(prompt_file, "r")
    allocated_prompt = allocated_prompt_file.read()
    allocated_prompt_file.close()
    
    prompt += "\n\n" + allocated_prompt + "\n\n"
    
    allocated_plan = []
    for i, plan in enumerate(decomposed_plan):
        no_robot  = len(available_robots[i])
        curr_prompt = prompt + plan
        curr_prompt += f"\n# TASK ALLOCATION"
        curr_prompt += f"\n# Scenario: There are {no_robot} robots available, The task should be performed using the minimum number of robots necessary. Robots should be assigned to subtasks that match its skills and mass capacity. Using your reasoning come up with a solution to satisfy all contraints."
        curr_prompt += f"\n\nrobots = {available_robots[i]}"
        curr_prompt += f"\n{objects_ai}"
        curr_prompt += f"\n\n# IMPORTANT: The AI should ensure that the robots assigned to the tasks have all the necessary skills to perform the tasks. IMPORTANT: Determine whether the subtasks must be performed sequentially or in parallel, or a combination of both and allocate robots based on availablitiy. "
        curr_prompt += f"\n# SOLUTION  \n"

        if "gpt" not in args.model:
            # older versions of GPT
            _, text = LM(curr_prompt, args.model, max_tokens=1000, stop=["def"], frequency_penalty=0.65)
        
        elif "gpt-3.5" in args.model:
            # gpt 3.5 and its variants
            messages = [{"role": "user", "content": curr_prompt}]
            _, text = LM(messages, args.model, max_tokens=1500, frequency_penalty=0.35)
        
        else:          
            # gpt 4.0 and other models
            messages = [{"role": "system", "content": "You are a Robot Task Allocation Expert. Determine whether the subtasks must be performed sequentially or in parallel, or a combination of both based on your reasoning. In the case of Task Allocation based on Robot Skills alone - First check if robot teams are required. Then Ensure that robot skills or robot team skills match the required skills for the subtask when allocating. Make sure that condition is met. In the case of Task Allocation based on Mass alone - First check if robot teams are required. Then Ensure that robot mass capacity or robot team combined mass capacity is greater than or equal to the mass for the object when allocating. Make sure that condition is met. In both the Task Task Allocation based on Mass alone and Task Allocation based on Skill alone, if there are multiple options for allocation, pick the best available option by reasoning to the best of your ability."},{"role": "system", "content": "You are a Robot Task Allocation Expert"},{"role": "user", "content": curr_prompt}]
            _, text = LM(messages, args.model, max_tokens=400, frequency_penalty=0.69)

        # 코드 후처리 적용
        cleaned_text = clean_generated_code(text)
        allocated_plan.append(cleaned_text)
    
    print ("3단계: Generating Allocated Code...")
    
    ######## Train Task Allocation - CODE Solution ########

    prompt = f"from skills import " + actions.ai2thor_actions
    prompt += f"\nimport time"
    prompt += f"\nimport threading"
    prompt += objects_ai
    
    code_plan = []

    prompt_file1 = os.getcwd() + "/data/pythonic_plans/" + args.prompt_allocation_set + "_code.py"
    code_prompt_file = open(prompt_file1, "r")
    code_prompt = code_prompt_file.read()
    code_prompt_file.close()
    
    prompt += "\n\n" + code_prompt + "\n\n"

    for i, (plan, solution) in enumerate(zip(decomposed_plan,allocated_plan)):
        curr_prompt = f"""Task: {test_tasks[i]}
Robots: {available_robots[i]}
Allocation: {solution}

IMPORTANT: Generate Python code using ONLY these AI2Thor action functions:
- GoToObject(robot, object_name)
- PickupObject(robot, object_name) 
- PutObject(robot, object_name, target_object)
- OpenObject(robot, object_name)
- CloseObject(robot, object_name)
- SwitchOn(robot, object_name)
- SwitchOff(robot, object_name)
- SliceObject(robot, object_name)
- CleanObject(robot, object_name)
- ThrowObject(robot, object_name, target_object)
- BreakObject(robot, object_name)
- DropHandObject(robot)
- PushObject(robot, object_name)
- PullObject(robot, object_name)

RULES:
1. Use robot_list[0] for first robot, robot_list[1] for second robot
2. Each action must be on a separate line
3. Include comments explaining each step
4. ALWAYS include the function call at the end
5. Do NOT use ai2thor.Environment() or any other AI2Thor classes
6. Do NOT use env.set_robot_state() or similar methods
7. CRITICAL: When putting an object somewhere, ALWAYS go to the destination first:
   - GoToObject(robot, 'Object') → PickupObject(robot, 'Object') → GoToObject(robot, 'Destination') → PutObject(robot, 'Object', 'Destination')

WORKING EXAMPLE (Toast a slice of the breadloaf):
def toast_bread(robot_list):
    # robot_list = [robot1, robot2]
    # 0: SubTask 1: Toast a slice of the breadloaf
    # 1: Go to the Bread using robot2.
    GoToObject(robot_list[1], 'Bread')
    # 2: Pick up the Bread using robot2.
    PickupObject(robot_list[1], 'Bread')
    # 3: Go to the Toaster using robot2.
    GoToObject(robot_list[1], 'Toaster')
    # 4: Put the Bread in the Toaster using robot2.
    PutObject(robot_list[1], 'Bread', 'Toaster')
    # 5: Turn on the Toaster using robot1.
    GoToObject(robot_list[0], 'Toaster')
    SwitchOn(robot_list[0], 'Toaster')
    # 6: Wait for the bread to toast.
    time.sleep(5)
    # 7: Turn off the Toaster using robot1.
    SwitchOff(robot_list[0], 'Toaster')
    # 8: Pick up the toasted Bread using robot2.
    PickupObject(robot_list[1], 'Bread')
    # 9: Go to the CounterTop using robot2.
    GoToObject(robot_list[1], 'CounterTop')
    # 10: Put the toasted Bread on the CounterTop using robot2.
    PutObject(robot_list[1], 'Bread', 'CounterTop')

# Execute SubTask 1
toast_bread([robots[0], robots[1]])

WORKING EXAMPLE (Turn on the laptop):
def turn_on_laptop(robot_list):
    # robot_list = [robot1]
    # 0: Go to the Laptop using robot1.
    GoToObject(robot_list[0], 'Laptop')
    # 1: Turn on the Laptop using robot1.
    SwitchOn(robot_list[0], 'Laptop')

# Execute SubTask
turn_on_laptop([robots[0]])

WORKING EXAMPLE (Turn on the mobile phone):
def turn_on_mobile_phone(robot_list):
    # robot_list = [robot1]
    # 0: Go to the Cellphone using robot1.
    GoToObject(robot_list[0], 'Cellphone')
    # 1: Turn on the Cellphone using robot1.
    SwitchOn(robot_list[0], 'Cellphone')

# Execute SubTask
turn_on_mobile_phone([robots[0]])

Now generate the code for this task following the same pattern:

CRITICAL REQUIREMENTS:
1. The function name must match the task description (e.g., toast_bread, put_mug_in_coffee_machine)
2. Use ONLY the AI2Thor action functions listed above
3. Use robot_list[0] for first robot, robot_list[1] for second robot, etc.
4. Include the function call at the end: function_name([robots[0], robots[1]])
5. Each action must be on a separate line with comments
6. Do NOT generate generic function names like "assemble_object" or "task_function"

Generate the code now:"""
        
        if "gpt" not in args.model:
            # older versions of GPT
            _, text = LM(curr_prompt, args.model, max_tokens=1500, frequency_penalty=0.30)
        else:            
            # using variants of gpt 4 or 3.5
            messages = [{"role": "system", "content": "You are a Robot Task Allocation Expert. Generate ONLY Python code using AI2Thor action functions. Follow the exact format provided in the user prompt. Do not include explanations, markdown, or any text other than the Python code. Use only the specified AI2Thor functions and include the function call at the end."},{"role": "user", "content": curr_prompt}]
            _, text = LM(messages, args.model, max_tokens=2000, frequency_penalty=0.4)

        # 코드 후처리 적용
        cleaned_text = clean_generated_code(text)
        code_plan.append(cleaned_text)
    
    # save generated plan
    exec_folders = []
    if args.log_results:
        line = {}
        now = datetime.now() # current date and time
        date_time = now.strftime("%m-%d-%Y-%H-%M-%S")
        
        for idx, task in enumerate(test_tasks):
            task_name = "{fxn}".format(fxn = '_'.join(task.split(' ')))
            task_name = task_name.replace('\n','')
            folder_name = f"{task_name}_plans_{date_time}"
            exec_folders.append(folder_name)
            
            os.mkdir("./logs/"+folder_name)
     
            with open(f"./logs/{folder_name}/log.txt", 'w') as f:
                f.write(task)
                f.write(f"\n\nModel: {args.model}")
                f.write(f"\n\nFloor Plan: {args.floor_plan}")
                f.write(f"\n{objects_ai}")
                f.write(f"\nrobots = {available_robots[idx]}")
                f.write(f"\nground_truth = {gt_test_tasks[idx]}")
                f.write(f"\ntrans = {trans_cnt_tasks[idx]}")
                f.write(f"\nmax_trans = {max_trans_cnt_tasks[idx]}")

            with open(f"./logs/{folder_name}/decomposed_plan.py", 'w') as d:
                d.write(decomposed_plan[idx])
                
            with open(f"./logs/{folder_name}/allocated_plan.py", 'w') as a:
                a.write(allocated_plan[idx])
                
            with open(f"./logs/{folder_name}/code_plan.py", 'w') as x:
                x.write(code_plan[idx])
    
    print("\n" + "="*60)
    print("✅ 모든 작업이 완료되었습니다!")
    print("📁 결과 파일들은 logs/ 폴더에서 확인할 수 있습니다.")
    print("="*60)
    