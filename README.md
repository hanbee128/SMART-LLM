# **SMART-LLM: Smart Multi-Agent Robot Task Planning using Large Language Models**

Shyam Sundar Kannan, Vishnunandan L. N. Venkatesh, and Byung-Cheol Min. 

Submitted to IEEE International Conference on Robotics and Automation (ICRA ), 2024

[Project Page](https://sites.google.com/view/smart-llm/) | [arXiv](https://arxiv.org/abs/2309.10062) | [Video](https://www.youtube.com/watch?v=mssTPl7ifyI)

**Abstract:** In this work, we introduce SMART-LLM, an innovative framework designed for embodied multi-robot task planning. SMART-LLM: Smart Multi-Agent Robot Task Planning using Large Language Models (LLMs), harnesses the power of LLMs to convert high-level task instructions provided as input into a multi-robot task plan. It accomplishes this by executing a series of stages, including task decomposition, coalition formation, and task allocation, all guided by programmatic LLM prompts within the few-shot prompting paradigm. We create a benchmark dataset designed for validating the multi-robot task planning problem, encompassing four distinct categories of high-level instructions that vary in task complexity. Our evaluation experiments span both simulation and real-world scenarios, demonstrating that the proposed model can achieve promising results for generating multi-robot task plans.

## Setup
Create a conda environment (or virtualenv):
```
conda create -n smartllm python==3.9
```

Install dependencies:
```
pip install -r requirments.txt
```

## Creating OpenAI API Key
The code relies on OpenAI API. Create an API Key at https://platform.openai.com/.

Create a file named ```api_key.txt``` in the root folder of the project and paste your OpenAI Key in the file. 

## Running Script
Run the following command to generate output execuate python scripts to perform the tasks in the given AI2Thor floor plans. 

Refer to https://ai2thor.allenai.org/demo for the layout of various AI2Thor floor plans.
```
python3 scripts/run_llm.py --floor-plan {floor_plan_no}
```
Note: Refer to the script for running it on different versions of GPT models and changing the test dataset. 

The above script should generate the executable code and store it in the ```logs``` folder.


Run the following script to execute the above generated scripts and execute it in an AI2THOR environment. 

The script requires command which needs to be executed as parameter. ```command``` needs to be the folder name in the ```logs``` folder where the executable plans generated are stored. 
```
python3 scripts/execute_plan.py --command {command}
```
## Dataset
The repository contains numerous commands and robots with various skill sets to perform heterogenous robot tasks. 

Refer to ```data\final_test\``` for the various tasks, robots available for the tasks, and the final state of the environment after the task for evaluation. 

The file name corresponds to the AI2THOR floor plans where the task will be executed. 

Refer to ```resources\robots.py``` for the list of robots used in the final test and the skills possessed by each robot. 


## Citation
If you find this work useful for your research, please consider citing:
```
@article{kannan2023smart,
    title={SMART-LLM: Smart Multi-Agent Robot Task Planning using Large Language Models},
  	author={Kannan, Shyam Sundar and Venkatesh, Vishnunandan LN and Min, Byung-Cheol},
  	journal={arXiv preprint arXiv:2309.10062},
 	year={2023}
}
```

---

# **SMART-LLM: 대규모 언어 모델을 활용한 스마트 다중 에이전트 로봇 작업 계획**

샴 순다르 칸난, 비슈누난단 L. N. 벤카테시, 그리고 민병철

2024년 IEEE 국제 로보틱스 및 자동화 컨퍼런스(ICRA)에 제출

[프로젝트 페이지](https://sites.google.com/view/smart-llm/) | [arXiv](https://arxiv.org/abs/2309.10062) | [비디오](https://www.youtube.com/watch?v=mssTPl7ifyI)

**초록:** 본 연구에서는 구체화된 다중 로봇 작업 계획을 위해 설계된 혁신적인 프레임워크인 SMART-LLM을 소개합니다. SMART-LLM: 대규모 언어 모델(LLM)을 활용한 스마트 다중 에이전트 로봇 작업 계획은 LLM의 힘을 활용하여 입력으로 제공되는 고수준 작업 지시사항을 다중 로봇 작업 계획으로 변환합니다. 이는 few-shot 프롬프팅 패러다임 내에서 프로그래밍적 LLM 프롬프트에 의해 안내되는 작업 분해, 연합 형성, 작업 할당을 포함한 일련의 단계를 실행함으로써 이를 달성합니다. 우리는 작업 복잡도가 다양한 고수준 지시사항의 네 가지 구별되는 범주를 포함하는 다중 로봇 작업 계획 문제를 검증하기 위해 설계된 벤치마크 데이터셋을 생성합니다. 우리의 평가 실험은 시뮬레이션과 실제 시나리오 모두에 걸쳐 있으며, 제안된 모델이 다중 로봇 작업 계획 생성에 대해 유망한 결과를 달성할 수 있음을 보여줍니다.

## 설정
conda 환경(또는 virtualenv) 생성:
```
conda create -n smartllm python==3.9
```

의존성 설치:
```
pip install -r requirments.txt
```

## API 키 설정
코드는 여러 LLM을 지원합니다. **보안을 위해 API 키는 파일에 저장하지 않고 실행할 때마다 입력받습니다.**

### API 키 획득 방법:
- **OpenAI**: https://platform.openai.com/에서 API 키 생성
- **Claude (Anthropic)**: https://console.anthropic.com/에서 API 키 생성  
- **Gemini (Google)**: https://makersuite.google.com/app/apikey에서 API 키 생성
- **Ollama (로컬)**: API 키 불필요

### Ollama 설치 (로컬 모델용)
```bash
# Ollama 설치 (Linux/Mac)
curl -fsSL https://ollama.ai/install.sh | sh

# 모델 다운로드 예시
ollama pull llama3
ollama pull tinyllama
```

## 스크립트 실행
주어진 AI2Thor 플로어 플랜에서 작업을 수행하기 위한 실행 가능한 파이썬 스크립트를 생성하려면 다음 명령어를 실행하세요.

다양한 AI2Thor 플로어 플랜의 레이아웃은 https://ai2thor.allenai.org/demo를 참조하세요.

### 기본 명령어 구조
```bash
python3 scripts/run_llm.py --floor-plan {floor_plan_no} --model {model_name} [옵션들]
```

### 명령어 옵션 상세 설명

#### 필수 인수 (Required Arguments)
- `--floor-plan FLOOR_PLAN`: AI2THOR 플로어 플랜 번호 (정수)
  - 예: `--floor-plan 6`, `--floor-plan 15`
  - 사용 가능한 플로어 플랜: 6, 15, 21, 201, 209, 303, 414

#### 플로어 플랜 환경 설명
각 플로어 플랜은 서로 다른 가정 환경을 시뮬레이션합니다:

- **FloorPlan 6**: **주방 환경** 🍳
  - 작업: 토마토 자르기, 상추 씻기, 뒤집개 버리기
  - 특징: 요리 관련 도구들 (칼, 냉장고, 싱크대, 가스레인지 등)
  - 복잡도: 기본

- **FloorPlan 15**: **복합 주방 환경** 🏠
  - 작업: 조명 제어, 냉장고 사용, 요리, 전자제품 조작
  - 특징: 다양한 가전제품 (전자레인지, 커피머신, 조명 등)
  - 복잡도: 중간

- **FloorPlan 21**: **고급 주방 환경** 👨‍🍳
  - 작업: 병렬 작업, 전자제품 조작, 요리
  - 특징: 복잡한 요리 작업과 전자제품 조작
  - 복잡도: 높음

- **FloorPlan 201**: **거실 환경** 🛋️
  - 작업: 물건 정리, 전자제품 조작, 조명 제어
  - 특징: 거실 가구 (소파, TV, 책상, 조명 등)
  - 복잡도: 중간

- **FloorPlan 209**: **거실/다이닝 환경** 🍽️
  - 작업: 물건 정리, 전자제품 조작, 조명 제어
  - 특징: 거실과 식당 공간이 결합된 환경
  - 복잡도: 중간

- **FloorPlan 303**: **침실 환경** 🛏️
  - 작업: 전자제품 조작, 물건 정리, 조명 제어
  - 특징: 침실 가구 (침대, 책상, 전자제품 등)
  - 복잡도: 중간

- **FloorPlan 414**: **욕실 환경** 🚿
  - 작업: 물 관리, 청소, 조명 제어
  - 특징: 욕실 시설 (욕조, 싱크대, 화장실 등)
  - 복잡도: 기본

#### 선택 인수 (Optional Arguments)
- `--model MODEL`: 사용할 LLM 모델 선택 (기본값: gpt-3.5-turbo)
  - **OpenAI**: `gpt-3.5-turbo`, `gpt-4`
  - **Gemini**: `gemini-2.5-flash`, `gemini-1.5-flash`, `gemini-2.0-flash-exp`
  - **Ollama**: `ollama:llama3`, `ollama:tinyllama`

- `--prompt-decompse-set SET`: 작업 분해 프롬프트 세트 (기본값: train_task_decompose)
  - 현재 지원: `train_task_decompose`

- `--prompt-allocation-set SET`: 작업 할당 프롬프트 세트 (기본값: train_task_allocation)
  - 현재 지원: `train_task_allocation`

- `--test-set SET`: 테스트 데이터셋 (기본값: final_test)
  - 현재 지원: `final_test`

- `--log-results BOOL`: 결과 로깅 여부 (기본값: True)
  - `True`: 결과를 logs 폴더에 저장
  - `False`: 결과 저장하지 않음

### 지원되는 모델:
- **OpenAI**: `gpt-3.5-turbo`, `gpt-4`
- **Gemini**: `gemini-2.5-flash`, `gemini-1.5-flash`, `gemini-2.0-flash-exp`
- **Ollama**: `ollama:llama3`, `ollama:tinyllama`

### 실행 과정
스크립트 실행 시 다음 3단계를 거쳐 로봇 작업 계획을 생성합니다:

1. **1단계: Generating Decompsed Plans** - 고수준 작업을 세부 작업으로 분해
2. **2단계: Generating Allocation Solution** - 로봇들에게 작업 할당
3. **3단계: Generating Allocated Code** - 실행 가능한 Python 코드 생성

### 사용 예시:

#### 기본 사용법
```bash
# 가장 간단한 사용법 (기본 모델: gpt-3.5-turbo)
python3 scripts/run_llm.py --floor-plan 6

# 특정 모델 지정
python3 scripts/run_llm.py --floor-plan 6 --model gpt-4
```

#### OpenAI 모델 사용
```bash
# GPT-4 사용 (API 키 입력 요구)
python3 scripts/run_llm.py --floor-plan 6 --model gpt-4
# 실행 시: "OpenAI API 키를 입력하세요: " 프롬프트가 나타남

# GPT-3.5-turbo 사용 (API 키 입력 요구)
python3 scripts/run_llm.py --floor-plan 6 --model gpt-3.5-turbo
# 실행 시: "OpenAI API 키를 입력하세요: " 프롬프트가 나타남
```

#### Gemini 모델 사용
```bash
# Gemini 1.5 Flash 사용 (API 키 입력 요구, 권장)
python3 scripts/run_llm.py --floor-plan 6 --model gemini-1.5-flash
# 실행 시: "Google Gemini API 키를 입력하세요: " 프롬프트가 나타남

# Gemini 2.5 Flash 사용 (API 키 입력 요구, 안전 필터 주의)
python3 scripts/run_llm.py --floor-plan 6 --model gemini-2.5-flash

# Gemini 2.0 Flash Exp 사용 (API 키 입력 요구)
python3 scripts/run_llm.py --floor-plan 6 --model gemini-2.0-flash-exp
```

#### Ollama 로컬 모델 사용
```bash
# Llama3 사용 (API 키 불필요)
python3 scripts/run_llm.py --floor-plan 6 --model ollama:llama3

# TinyLlama 사용 (API 키 불필요)
python3 scripts/run_llm.py --floor-plan 6 --model ollama:tinyllama
```

#### 환경별 사용 예시
```bash
# 주방 환경 (기본)
python3 scripts/run_llm.py --floor-plan 6 --model gemini-1.5-flash

# 복합 주방 환경 (중간 복잡도)
python3 scripts/run_llm.py --floor-plan 15 --model gpt-4

# 고급 주방 환경 (높은 복잡도)
python3 scripts/run_llm.py --floor-plan 21 --model gpt-4

# 거실 환경
python3 scripts/run_llm.py --floor-plan 201 --model gemini-1.5-flash

# 거실/다이닝 환경
python3 scripts/run_llm.py --floor-plan 209 --model ollama:llama3

# 침실 환경
python3 scripts/run_llm.py --floor-plan 303 --model gemini-1.5-flash

# 욕실 환경
python3 scripts/run_llm.py --floor-plan 414 --model ollama:tinyllama
```

#### 고급 옵션 사용
```bash
# 로깅 비활성화
python3 scripts/run_llm.py --floor-plan 6 --model gpt-4 --log-results False

# 모든 옵션 지정
python3 scripts/run_llm.py --floor-plan 6 --model gpt-4 --prompt-decompse-set train_task_decompose --prompt-allocation-set train_task_allocation --test-set final_test --log-results True
```

### 생성되는 결과 파일
스크립트 실행 후 `logs/` 폴더에 다음 파일들이 생성됩니다:

- `{작업명}_plans_{타임스탬프}/` 폴더
  - `log.txt`: 실행 로그 및 설정 정보
  - `decomposed_plan.py`: 작업 분해 계획
  - `allocated_plan.py`: 로봇 할당 계획
  - `code_plan.py`: 실행 가능한 Python 코드

### 생성된 계획 실행하기
생성된 스크립트를 AI2THOR 환경에서 실행하려면:

```bash
python3 scripts/execute_plan.py --command {폴더명}
```

**예시:**
```bash
# 생성된 폴더명 확인
ls logs/

# 해당 폴더로 실행
python3 scripts/execute_plan.py --command Slice_the_tomato_plans_09-04-2025-10-33-45
```

### 도움말 보기
```bash
# 전체 도움말
python3 scripts/run_llm.py --help

# execute_plan.py 도움말
python3 scripts/execute_plan.py --help
```

## 데이터셋
이 저장소는 다양한 기술 세트를 가진 수많은 명령어와 로봇을 포함하여 이질적인 로봇 작업을 수행합니다.

다양한 작업, 작업에 사용 가능한 로봇, 평가를 위한 작업 후 환경의 최종 상태는 ```data\final_test\```를 참조하세요.

파일 이름은 작업이 실행될 AI2THOR 플로어 플랜에 해당합니다.

최종 테스트에서 사용된 로봇 목록과 각 로봇이 보유한 기술은 ```resources\robots.py```를 참조하세요.

## 인용
이 연구가 귀하의 연구에 유용하다고 생각하시면, 다음을 인용해 주시기 바랍니다:
```
@article{kannan2023smart,
    title={SMART-LLM: Smart Multi-Agent Robot Task Planning using Large Language Models},
  	author={Kannan, Shyam Sundar and Venkatesh, Vishnunandan LN and Min, Byung-Cheol},
  	journal={arXiv preprint arXiv:2309.10062},
 	year={2023}
}
```
