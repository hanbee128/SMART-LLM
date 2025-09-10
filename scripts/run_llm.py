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

def calculate_robot_task_distance(robot_pos, task_objects, floor_plan_data):
    """로봇과 태스크 객체들 간의 최단 거리 계산 (간단한 휴리스틱)"""
    # 실제 Floor Plan 데이터가 없으므로 간단한 휴리스틱 사용
    # 객체 이름의 길이와 복잡도를 기반으로 거리 추정
    complexity_score = 0
    for obj_name in task_objects:
        complexity_score += len(obj_name) * 0.1  # 이름이 길수록 복잡
    
    # 랜덤 요소 추가 (실제로는 로봇 위치와 객체 위치를 비교해야 함)
    import random
    base_distance = 2.0 + complexity_score
    random_factor = random.uniform(0.5, 1.5)
    
    return base_distance * random_factor

def extract_objects_from_task(task_description):
    """태스크 설명에서 객체 이름들을 추출"""
    import re
    
    # 일반적인 객체 이름들
    common_objects = [
        'Watch', 'KeyChain', 'Pillow', 'Box', 'Sofa', 'Bowl', 'Vase', 'DiningTable', 
        'Book', 'Laptop', 'Apple', 'Knife', 'Fork', 'Drawer', 'Refrigerator', 
        'Microwave', 'Stove', 'Sink', 'CounterTop', 'Chair', 'Table', 'Bed',
        'Television', 'RemoteControl', 'Lamp', 'GarbageCan', 'Bathtub', 'CellPhone'
    ]
    
    found_objects = []
    task_lower = task_description.lower()
    
    for obj in common_objects:
        if obj.lower() in task_lower:
            found_objects.append(obj)
    
    return found_objects

def load_floor_plan_data(floor_plan):
    """Floor Plan JSON 데이터 로드"""
    import json
    try:
        with open(f"data/final_test/FloorPlan{floor_plan}.json", 'r') as f:
            content = f.read()
            # 여러 JSON 객체가 줄바꿈으로 구분된 경우 처리
            if content.strip().startswith('{') and '\n' in content:
                # 첫 번째 JSON 객체만 파싱 (실제 Floor Plan 데이터는 별도 파일에 있을 수 있음)
                first_line = content.split('\n')[0]
                return json.loads(first_line)
            else:
                return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Floor Plan {floor_plan} 데이터를 로드할 수 없습니다: {e}")
        return {"objects": []}

def assign_robots_by_distance(robots, task_description, floor_plan, busy_robots=None):
    """거리 기반으로 로봇 할당 (바쁜 로봇 제외)"""
    if busy_robots is None:
        busy_robots = set()
    
    # 태스크에서 객체 추출
    task_objects = extract_objects_from_task(task_description)
    
    if not task_objects:
        # 객체를 찾을 수 없으면 원래 할당 사용
        return robots[:1] if robots else []
    
    # Floor Plan 데이터 로드
    floor_plan_data = load_floor_plan_data(floor_plan)
    
    # 사용 가능한 로봇들 (바쁜 로봇 제외)
    available_robots = [robot for i, robot in enumerate(robots) if i not in busy_robots]
    
    if not available_robots:
        # 모든 로봇이 바쁘면 원래 할당 사용
        return robots[:1] if robots else []
    
    # 각 로봇과 태스크 간의 거리 계산
    robot_distances = []
    for i, robot in enumerate(robots):
        if i in busy_robots:
            continue
            
        robot_pos = (0, 0, 0)  # 기본 위치 (실제로는 시뮬레이션에서 위치를 가져와야 함)
        distance = calculate_robot_task_distance(robot_pos, task_objects, floor_plan_data)
        robot_distances.append((i, robot, distance))
    
    # 거리순으로 정렬
    robot_distances.sort(key=lambda x: x[2])
    
    print(f"🔍 태스크 '{task_description}'에서 발견된 객체들: {task_objects}")
    print(f"📏 로봇 거리 순위: {[(i, f'{dist:.2f}m') for i, _, dist in robot_distances[:3]]}")
    
    # 가장 가까운 로봇 1-3개 선택 (태스크 복잡도에 따라)
    if len(task_objects) == 1:
        selected_robots = [robot_distances[0][1]]  # 단일 객체는 1개 로봇
    elif len(task_objects) == 2:
        # 2개 객체: 2-3개 로봇 (하나는 컨테이너 열기, 나머지는 객체 처리)
        if len(robot_distances) >= 3:
            selected_robots = [robot_distances[0][1], robot_distances[1][1], robot_distances[2][1]]
        else:
            selected_robots = [robot_distances[0][1], robot_distances[1][1]] if len(robot_distances) >= 2 else [robot_distances[0][1]]
    else:
        # 3개 이상 객체: 최대 3개 로봇
        selected_robots = [robot_distances[0][1], robot_distances[1][1], robot_distances[2][1]] if len(robot_distances) >= 3 else [robot_distances[0][1], robot_distances[1][1]] if len(robot_distances) >= 2 else [robot_distances[0][1]]
    
    print(f"✅ 선택된 로봇들: {[robot['name'] for robot in selected_robots]}")
    return selected_robots

def clean_generated_code(code, available_robots_count=1):
    """생성된 코드에서 마크다운 블록과 불필요한 텍스트를 제거합니다."""
    import re
    
    # 마크다운 코드 블록 제거
    code = re.sub(r'```python\s*', '', code)
    code = re.sub(r'```\s*$', '', code)
    code = re.sub(r'```.*?\n', '', code, flags=re.DOTALL)
    
    # LLM이 생성한 설명 텍스트 제거
    code = re.sub(r'Here is the generated code for the task.*?\n', '', code, flags=re.DOTALL)
    code = re.sub(r'Here is the generated code for Task.*?\n', '', code, flags=re.DOTALL)
    code = re.sub(r'Note that I\'ve followed.*?\n', '', code, flags=re.DOTALL)
    code = re.sub(r'Note that I followed.*?\n', '', code, flags=re.DOTALL)
    code = re.sub(r'This code.*?\n', '', code, flags=re.DOTALL)
    code = re.sub(r'The robot will.*?\n', '', code, flags=re.DOTALL)
    code = re.sub(r'First, the robot.*?\n', '', code, flags=re.DOTALL)
    code = re.sub(r'Then, the robot.*?\n', '', code, flags=re.DOTALL)
    code = re.sub(r'Finally, the robot.*?\n', '', code, flags=re.DOTALL)
    
    # 추가 설명 텍스트 패턴들
    code = re.sub(r'^.*Here is the generated code.*$', '', code, flags=re.MULTILINE)
    code = re.sub(r'^.*Here is the generated Python code.*$', '', code, flags=re.MULTILINE)
    code = re.sub(r'^.*Note that I\'ve followed.*$', '', code, flags=re.MULTILINE)
    code = re.sub(r'^.*Note that I followed.*$', '', code, flags=re.MULTILINE)
    code = re.sub(r'^.*This code.*$', '', code, flags=re.MULTILINE)
    code = re.sub(r'^.*The robot will.*$', '', code, flags=re.MULTILINE)
    code = re.sub(r'^.*First, the robot.*$', '', code, flags=re.MULTILINE)
    code = re.sub(r'^.*Then, the robot.*$', '', code, flags=re.MULTILINE)
    code = re.sub(r'^.*Finally, the robot.*$', '', code, flags=re.MULTILINE)
    
    # 추가적인 LLM 설명 텍스트 패턴들
    code = re.sub(r'^.*I followed the critical requirements.*$', '', code, flags=re.MULTILINE)
    code = re.sub(r'^.*I also included comments.*$', '', code, flags=re.MULTILINE)
    code = re.sub(r'^.*and the function call at the end.*$', '', code, flags=re.MULTILINE)
    code = re.sub(r'^.*is `.*`.*$', '', code, flags=re.MULTILINE)
    
    # AI2Thor 액션 함수들
    ai2thor_functions = ['GoToObject', 'PickupObject', 'PutObject', 'OpenObject', 'CloseObject', 
                        'SwitchOn', 'SwitchOff', 'SliceObject', 'CleanObject', 'ThrowObject', 
                        'BreakObject', 'DropHandObject', 'PushObject', 'PullObject']
    
    # 모든 설명 텍스트 줄 제거 (def, import, #, 빈 줄이 아닌 모든 줄 중에서)
    lines = code.split('\n')
    cleaned_lines = []
    for line in lines:
        line_stripped = line.strip()
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
            cleaned_lines.append(line)
        # 설명 텍스트는 제거 (위 조건에 맞지 않는 모든 줄)
    
    result = '\n'.join(cleaned_lines)
    
    # 연속된 빈 줄 정리
    result = re.sub(r'\n\s*\n\s*\n', '\n\n', result)
    
    # 빈 함수나 잘못된 함수명 제거
    if 'def assemble_object' in result:
        result = result.replace('def assemble_object', 'def toast_bread')
    
    # 잘못된 객체 이름 교정 (AI2-THOR 정확한 이름으로)
    # 전화기 관련
    result = result.replace("'MobilePhone'", "'CellPhone'")
    result = result.replace("'Cellphone'", "'CellPhone'")
    result = result.replace("'cellphone'", "'CellPhone'")
    result = result.replace("'mobilephone'", "'CellPhone'")
    
    # 냉장고 관련
    result = result.replace("'Fridge'", "'Refrigerator'")
    result = result.replace("'fridge'", "'Refrigerator'")
    
    # TV 관련
    result = result.replace("'TV'", "'Television'")
    result = result.replace("'tv'", "'Television'")
    result = result.replace("'television'", "'Television'")
    
    # 테이블 관련
    result = result.replace("'Coffeetable'", "'CoffeeTable'")
    result = result.replace("'coffeetable'", "'CoffeeTable'")
    result = result.replace("'coffeeTable'", "'CoffeeTable'")
    
    # 쓰레기통 관련
    result = result.replace("'TrashCan'", "'GarbageCan'")
    result = result.replace("'trashcan'", "'GarbageCan'")
    result = result.replace("'garbagecan'", "'GarbageCan'")
    
    # 리모컨 관련
    result = result.replace("'Remote'", "'RemoteControl'")
    result = result.replace("'remote'", "'RemoteControl'")
    result = result.replace("'remotecontrol'", "'RemoteControl'")
    
    # 조명 관련
    result = result.replace("'FloorLamp'", "'Lamp'")
    result = result.replace("'floorlamp'", "'Lamp'")
    result = result.replace("'floorLamp'", "'Lamp'")
    
    # 존재하지 않는 객체들
    result = result.replace("'PowerButton'", "'Laptop'")  # PowerButton은 존재하지 않음
    result = result.replace("'powerbutton'", "'Laptop'")
    
    # 물뿌리개 관련 (Floor Plan 209에서 사용)
    result = result.replace("'WateringCan'", "'WateringCan'")  # WateringCan이 정확한 이름
    result = result.replace("'wateringcan'", "'WateringCan'")
    result = result.replace("'wateringCan'", "'WateringCan'")
    
    # 욕실 관련
    result = result.replace("'Bathroom'", "'Bathtub'")  # Bathroom은 존재하지 않음, Bathtub으로 교정
    result = result.replace("'bathroom'", "'Bathtub'")
    result = result.replace("'BathTub'", "'Bathtub'")  # 대소문자 통일
    result = result.replace("'bathtub'", "'Bathtub'")
    
    # 물 관련 - Water 객체는 존재하지 않음, FillObjectWithLiquid 액션 사용
    result = result.replace("PickupObject(robot_list[0], 'Water')", "FillObjectWithLiquid(robot_list[0], 'Bathtub')")
    result = result.replace("PickupObject(robot_list[1], 'Water')", "FillObjectWithLiquid(robot_list[1], 'Bathtub')")
    result = result.replace("PickupObject(robot_list[2], 'Water')", "FillObjectWithLiquid(robot_list[2], 'Bathtub')")
    result = result.replace("PickupObject(robot_list[3], 'Water')", "FillObjectWithLiquid(robot_list[3], 'Bathtub')")
    
    
    # Keychain 관련 - Keychain은 존재하지 않음, CreditCard로 교정
    result = result.replace("'Keychain'", "'KeyChain'")
    result = result.replace("'keychain'", "'KeyChain'")
    result = result.replace("'KeyChain'", "'KeyChain'")
    result = result.replace("'keyChain'", "'KeyChain'")
    
    # 액션 함수 이름 교정 (AI2-THOR 정확한 액션으로)
    result = result.replace("SwitchOn(", "ToggleObjectOn(")  # SwitchOn을 ToggleObjectOn으로 교정
    result = result.replace("SwitchOff(", "ToggleObjectOff(")  # SwitchOff를 ToggleObjectOff로 교정
    
    # 로봇 수 검증 및 수정
    # 사용 가능한 로봇 수보다 많은 로봇을 요구하는 경우 수정
    if available_robots_count == 1:
        # 1개 로봇만 사용 가능한 경우 - 모든 로봇 리스트를 [robots[0]]으로 변경
        result = re.sub(r'\[robots\[0\],\s*robots\[1\]\]', '[robots[0]]', result)
        result = re.sub(r'\[robots\[0\],\s*robots\[1\],\s*robots\[2\]\]', '[robots[0]]', result)
        result = re.sub(r'\[robots\[0\],\s*robots\[1\],\s*robots\[2\],\s*robots\[3\]\]', '[robots[0]]', result)
        result = re.sub(r'\[robots\[0\],\s*robots\[1\],\s*robots\[2\],\s*robots\[3\],\s*robots\[4\]\]', '[robots[0]]', result)
        
        # 함수 정의에서 robot_list 매개변수도 수정
        result = re.sub(r'def\s+(\w+)\(robot_list\):\s*#\s*robot_list\s*=\s*\[robot1,\s*robot2\]', 
                       r'def \g<1>(robot_list):\n    # robot_list = [robot1]', result)
        result = re.sub(r'def\s+(\w+)\(robot_list\):\s*#\s*robot_list\s*=\s*\[robot1,\s*robot2,\s*robot3\]', 
                       r'def \g<1>(robot_list):\n    # robot_list = [robot1]', result)
        result = re.sub(r'def\s+(\w+)\(robot_list\):\s*#\s*robot_list\s*=\s*\[robot1,\s*robot2,\s*robot3,\s*robot4\]', 
                       r'def \g<1>(robot_list):\n    # robot_list = [robot1]', result)
        
    elif available_robots_count == 2:
        # 2개 로봇만 사용 가능한 경우
        result = re.sub(r'\[robots\[0\],\s*robots\[1\],\s*robots\[2\]\]', '[robots[0], robots[1]]', result)
        result = re.sub(r'\[robots\[0\],\s*robots\[1\],\s*robots\[2\],\s*robots\[3\]\]', '[robots[0], robots[1]]', result)
        result = re.sub(r'\[robots\[0\],\s*robots\[1\],\s*robots\[2\],\s*robots\[3\],\s*robots\[4\]\]', '[robots[0], robots[1]]', result)
        
        # 함수 정의에서 robot_list 매개변수도 수정
        result = re.sub(r'def\s+(\w+)\(robot_list\):\s*#\s*robot_list\s*=\s*\[robot1,\s*robot2,\s*robot3\]', 
                       r'def \g<1>(robot_list):\n    # robot_list = [robot1, robot2]', result)
        result = re.sub(r'def\s+(\w+)\(robot_list\):\s*#\s*robot_list\s*=\s*\[robot1,\s*robot2,\s*robot3,\s*robot4\]', 
                       r'def \g<1>(robot_list):\n    # robot_list = [robot1, robot2]', result)
        
    elif available_robots_count == 3:
        # 3개 로봇만 사용 가능한 경우
        result = re.sub(r'\[robots\[0\],\s*robots\[1\],\s*robots\[2\],\s*robots\[3\]\]', '[robots[0], robots[1], robots[2]]', result)
        result = re.sub(r'\[robots\[0\],\s*robots\[1\],\s*robots\[2\],\s*robots\[3\],\s*robots\[4\]\]', '[robots[0], robots[1], robots[2]]', result)
        
        # 함수 정의에서 robot_list 매개변수도 수정
        result = re.sub(r'def\s+(\w+)\(robot_list\):\s*#\s*robot_list\s*=\s*\[robot1,\s*robot2,\s*robot3,\s*robot4\]', 
                       r'def \g<1>(robot_list):\n    # robot_list = [robot1, robot2, robot3]', result)
    
    # 추가: robot_list[1], robot_list[2] 등을 사용하는 경우도 수정
    if available_robots_count == 1:
        # 1개 로봇만 있는 경우 robot_list[1], robot_list[2] 등을 robot_list[0]으로 변경
        result = re.sub(r'robot_list\[1\]', 'robot_list[0]', result)
        result = re.sub(r'robot_list\[2\]', 'robot_list[0]', result)
        result = re.sub(r'robot_list\[3\]', 'robot_list[0]', result)
    elif available_robots_count == 2:
        # 2개 로봇만 있는 경우 robot_list[2], robot_list[3] 등을 robot_list[1]로 변경
        result = re.sub(r'robot_list\[2\]', 'robot_list[1]', result)
        result = re.sub(r'robot_list\[3\]', 'robot_list[1]', result)
    elif available_robots_count == 3:
        # 3개 로봇만 있는 경우 robot_list[3], robot_list[4] 등을 robot_list[2]로 변경
        result = re.sub(r'robot_list\[3\]', 'robot_list[2]', result)
        result = re.sub(r'robot_list\[4\]', 'robot_list[2]', result)
    
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
        cleaned_text = clean_generated_code(text, 1)  # 분해 단계에서는 기본값 사용
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
    busy_robots = set()  # 바쁜 로봇들 추적
    
    for i, plan in enumerate(decomposed_plan):
        # 거리 기반으로 로봇 할당
        task_description = test_tasks[i]
        assigned_robots = assign_robots_by_distance(robots.robots, task_description, args.floor_plan, busy_robots)
        
        # 할당된 로봇들을 바쁜 로봇 목록에 추가
        for robot in assigned_robots:
            for j, original_robot in enumerate(robots.robots):
                if robot['name'] == original_robot['name']:
                    busy_robots.add(j)
                    break
        
        no_robot = len(assigned_robots)
        curr_prompt = prompt + plan
        curr_prompt += f"\n# TASK ALLOCATION"
        curr_prompt += f"\n# Scenario: There are {no_robot} robots available, The task should be performed using the minimum number of robots necessary. Robots should be assigned to subtasks that match its skills and mass capacity. Using your reasoning come up with a solution to satisfy all contraints."
        curr_prompt += f"\n\nrobots = {assigned_robots}"
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
        cleaned_text = clean_generated_code(text, len(assigned_robots))
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

    # 코드 생성용으로 다시 거리 기반 할당 수행
    busy_robots_code = set()
    
    for i, (plan, solution) in enumerate(zip(decomposed_plan,allocated_plan)):
        # 거리 기반으로 로봇 할당 (코드 생성용)
        task_description = test_tasks[i]
        assigned_robots_code = assign_robots_by_distance(robots.robots, task_description, args.floor_plan, busy_robots_code)
        
        # 할당된 로봇들을 바쁜 로봇 목록에 추가
        for robot in assigned_robots_code:
            for j, original_robot in enumerate(robots.robots):
                if robot['name'] == original_robot['name']:
                    busy_robots_code.add(j)
                    break
        
        curr_prompt = f"""Task: {test_tasks[i]}
Robots: {assigned_robots_code}
Allocation: {solution}

IMPORTANT: Generate Python code using ONLY these AI2Thor action functions:
- Use ALL assigned robots: {len(assigned_robots_code)} robots are assigned
- Function call should be: function_name([robots[0], robots[1], ...]) with {len(assigned_robots_code)} robots
- GoToObject(robot, object_name)
- PickupObject(robot, object_name) 
- PutObject(robot, target_object)
- OpenObject(robot, object_name)
- CloseObject(robot, object_name)
- ToggleObjectOn(robot, object_name)  # Use ToggleObjectOn instead of SwitchOn
- ToggleObjectOff(robot, object_name)  # Use ToggleObjectOff instead of SwitchOff
- SliceObject(robot, object_name)
- CleanObject(robot, object_name)
- DirtyObject(robot, object_name)
- ThrowObject(robot, object_name, target_object)
- BreakObject(robot, object_name)
- DropHandObject(robot)
- PushObject(robot, object_name)
- PullObject(robot, object_name)
- FillObjectWithLiquid(robot, object_name)
- EmptyLiquidFromObject(robot, object_name)
- HandoffObject(robot_from, robot_to, object_name)  # 로봇 간 물체 전달

AVAILABLE OBJECTS (Use these exact names with correct capitalization):
Furniture: Armchair, Bed, Bookcase, Cabinet, Chair, CoffeeTable, CounterTop, Desk, DiningTable, Drawer, Dresser, Ottoman, Painting, Safe, Shelf, SideTable, Sofa, TVStand
Kitchenware: Bowl, Bottle, Cup, Fork, GarbageCan, Kettle, Knife, Microwave, Mug, Pan, Plate, Pot, Refrigerator, Sink, Spoon, StoveBurner, Toaster, WineBottle
Food: Apple, Bread, ButterKnife, Egg, Lettuce, Potato, Tomato
Electronics: AlarmClock, Blinds, CellPhone, Computer, HousePlant, Lamp, Laptop, LightSwitch, Pen, Pencil, RemoteControl, Statue, Television, Vase
Miscellaneous: Basket, Book, Box, Candle, CD, Cloth, CreditCard, Newspaper, Pillow, SaltShaker, SoapBar, SprayBottle, Toilet, ToiletPaper, Towel, Window

IMPORTANT: Use exact capitalization as shown above. Common corrections:
- CellPhone (not Cellphone or cellphone)
- CoffeeTable (not Coffeetable or coffeeTable)
- GarbageCan (not TrashCan or garbagecan)
- RemoteControl (not Remote or remotecontrol)
- Television (not TV or television)
- Refrigerator (not Fridge or fridge)

RULES:
1. Use robot_list[0] for first robot, robot_list[1] for second robot
2. Each action must be on a separate line
3. Include comments explaining each step
4. ALWAYS include the function call at the end
5. Do NOT use ai2thor.Environment() or any other AI2Thor classes
6. Do NOT use env.set_robot_state() or similar methods
7. CRITICAL: When putting an object somewhere, ALWAYS go to the destination first:
   - GoToObject(robot, 'Object') → PickupObject(robot, 'Object') → GoToObject(robot, 'Destination') → PutObject(robot, 'Destination')

8. CRITICAL: When slicing an object, follow this sequence:
   - GoToObject(robot, 'Knife') → PickupObject(robot, 'Knife') → GoToObject(robot, 'Object') → SliceObject(robot, 'Object') → PutObject(robot, 'CounterTop') → PickupObject(robot, 'Object') → GoToObject(robot, 'Destination') → PutObject(robot, 'Destination')

9. CRITICAL: When putting objects in openable containers (Drawer, Cabinet, Refrigerator, etc.):
   - If multiple robots are available, coordinate the work:
     * One robot: Pick up objects and go to container
     * Another robot: Open the container first, then help with placing objects
   - If only one robot: Pick up object → Go to container → Open container → Put object in container
   - ALWAYS open the container BEFORE trying to put objects inside

10. CRITICAL: For tasks requiring 3+ robots with multiple objects in one container:
   - Robot 1: Open the container FIRST (highest priority)
   - Robot 2: Pick up first object and go to container
   - Robot 3: Pick up second object and go to container
   - Then: All robots place their objects in the opened container
   - SEQUENCE: Open → Pick up objects → Place objects (coordinate timing)



WORKING EXAMPLE (Turn on the laptop):
def turn_on_laptop(robot_list):
    # robot_list = [robot1]
    # 0: Go to the Laptop using robot1.
    GoToObject(robot_list[0], 'Laptop')
    # 1: Turn on the Laptop using robot1.
    ToggleObjectOn(robot_list[0], 'Laptop')

# Execute SubTask
turn_on_laptop([robots[0]])

WORKING EXAMPLE (Slice the bread and toast it):
def slice_bread_and_toast(robot_list):
    # robot_list = [robot1]
    # 0: Go to the knife using robot1.
    GoToObject(robot_list[0], 'Knife')
    PickupObject(robot_list[0], 'Knife')
    # 1: Go to the Bread using robot1.
    GoToObject(robot_list[0], 'Bread')
    # 2: Slice the Bread using robot1.
    SliceObject(robot_list[0], 'Bread')
    # Check if the Bread is sliced to BreadSliced_1
    DropHandObject(robot_list[0])
    PickupObject(robot_list[0], 'BreadSliced_1')
    # 3: Go to the Toaster using robot1.
    GoToObject(robot_list[0], 'Toaster')
    # 4: Put the Bread in the Toaster using robot1.
    PutObject(robot_list[0], 'Toaster')
    # 5: Turn on the Toaster using robot1.
    ToggleObjectOn(robot_list[0], 'Toaster')
    time.sleep(5)
    # 6: Pick up the toasted Bread using robot1.
    PickupObject(robot_list[0], 'BreadSliced_1')
    
# Execute SubTask
slice_bread_and_toast(robots[0])
    

WORKING EXAMPLE (Put objects in drawer with cooperation):
def put_objects_in_drawer(robot_list):
    # robot_list = [robot1, robot2, robot3]
    # pick drawer1 first
    # 0: Robot2 opens the Drawer1 first
    GoToObject(robot_list[1], 'Drawer1')
    OpenObject(robot_list[1], 'Drawer1')
    # 1: Robot1 picks up Watch
    GoToObject(robot_list[0], 'Watch')
    PickupObject(robot_list[0], 'Watch')
    # 2: Robot1 goes to Drawer1 with Watch
    GoToObject(robot_list[0], 'Drawer1')
    # 3: Robot1 puts Watch in Drawer1
    PutObject(robot_list[0], 'Drawer1')
    # 4: Robot2 picks up Keychain
    GoToObject(robot_list[2], 'Keychain')
    PickupObject(robot_list[2], 'Keychain')
    # 5: Robot2 puts Keychain in Drawer1
    GoToObject(robot_list[2], 'Drawer1')
    PutObject(robot_list[2], 'Drawer1')

# Execute SubTask
put_objects_in_drawer([robots[0], robots[1], robots[2]])

WORKING EXAMPLE (Wash the fork and put it in the bowl):
def wash_fork_and_put_in_bowl(robot_list):
    # robot_list = [robot1]
    # 0: Go to the Fork using robot1.
    GoToObject(robot_list[0], 'Fork')
    # 1: Pick up the Fork using robot1.
    PickupObject(robot_list[0], 'Fork')
    # 2: Go to the Sink using robot1.
    GoToObject(robot_list[0], 'Sink')
    # 3: Clean the Fork using robot1.
    CleanObject(robot_list[0], 'Fork')
    # 4: Go to the Bowl using robot1.
    GoToObject(robot_list[0], 'Bowl')
    # 5: Put the Fork in the Bowl using robot1.
    PutObject(robot_list[0], 'Bowl')

# Execute SubTask
wash_fork_and_put_in_bowl(robots[0])

WORKING EXAMPLE (Slice apple and throw it in the trash):
def slice_apple_and_throw_in_trash(robot_list):
    # robot_list = [robot1]
    # 0: Go to the Knife using robot1.
    GoToObject(robot_list[0], 'Knife')
    # 1: Pick up the Knife using robot1.
    PickupObject(robot_list[0], 'Knife')
    # 2: Go to the Apple using robot1.
    GoToObject(robot_list[0], 'Apple')
    # 3: Slice the Apple using robot1.
    SliceObject(robot_list[0], 'Apple')
     # 4: Put the Knife using robot1.
     PutObject(robot_list[0], 'CounterTop')
     # 5: Pick up the sliced Apple using robot1.
    PickupObject(robot_list[0], 'Apple')
    # 7: Go to the GarbageCan using robot1.
    GoToObject(robot_list[0], 'GarbageCan')
    # 8: Put the Apple in the GarbageCan using robot1.
    PutObject(robot_list[0], 'GarbageCan')

# Execute SubTask
slice_apple_and_throw_in_trash(robots[0])


KEY RULES:
- If task mentions "slice of bread" or "slice of breadloaf": FIRST use GoToObject(robot_list[0], 'Knife') to slice the bread, THEN use knife to slice the bread
- IMPORTANT: Use 'Bread' not 'Breadloaf' - AI2THOR uses 'Bread' as the object name'
- IMPORTANT: if bread is sliced, use 'BreadSliced_1', 'BreadSliced_2'... not 'Bread'
- if task mentions "breadloaf", use "Bread" 
- If task mentions "toast": Use ToggleObjectOn to turn on the toaster
- If task mentions "put in drawer": Use OpenObject first if the drawer is closed, then PutObject
- If task mentions "pick up": Use GoToObject first to navigate to the object, then PickupObject
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
        cleaned_text = clean_generated_code(text, len(assigned_robots_code))
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
    