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

## OpenAI API 키 생성
코드는 OpenAI API에 의존합니다. https://platform.openai.com/에서 API 키를 생성하세요.

프로젝트의 루트 폴더에 ```api_key.txt```라는 파일을 생성하고 파일에 OpenAI 키를 붙여넣으세요.

## 스크립트 실행
주어진 AI2Thor 플로어 플랜에서 작업을 수행하기 위한 실행 가능한 파이썬 스크립트를 생성하려면 다음 명령어를 실행하세요.

다양한 AI2Thor 플로어 플랜의 레이아웃은 https://ai2thor.allenai.org/demo를 참조하세요.
```
python3 scripts/run_llm.py --floor-plan {floor_plan_no}
```
참고: 다양한 GPT 모델 버전에서 실행하고 테스트 데이터셋을 변경하는 방법은 스크립트를 참조하세요.

위 스크립트는 실행 가능한 코드를 생성하고 ```logs``` 폴더에 저장해야 합니다.

생성된 스크립트를 실행하고 AI2THOR 환경에서 실행하려면 다음 스크립트를 실행하세요.

스크립트는 실행해야 할 명령어를 매개변수로 필요로 합니다. ```command```는 생성된 실행 가능한 계획이 저장된 ```logs``` 폴더의 폴더 이름이어야 합니다.
```
python3 scripts/execute_plan.py --command {command}
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
