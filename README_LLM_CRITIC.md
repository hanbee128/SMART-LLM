# 🤖 LLM Critic - 코드 검증 시스템

## 개요
SMART-LLM에 **LLM Critic** 기능이 추가되었습니다! 이는 생성된 코드의 품질을 검증하고 개선하는 AI 검증자입니다.

## 🔍 LLM Critic이 하는 일

### 1. **코드 품질 검증**
- AI2Thor 액션 함수 올바른 사용
- 객체 이름 정확성 (대소문자, 이름)
- 객체 상태 변화 처리 (AppleSliced_1, BreadSliced_1 등)
- 로봇 할당 정확성
- 액션 순서 준수

### 2. **자동 코드 개선**
- 문제가 발견되면 자동으로 수정된 코드 제공
- 문법 오류 수정
- 들여쓰기 오류 수정
- 논리적 오류 수정

### 3. **검증 기준**
```
1. AI2Thor 액션 함수 사용
2. 객체 이름 정확성
3. 객체 상태 변화 처리
4. 로봇 할당 정확성
5. 액션 순서 준수
6. 컨테이너 처리 (OpenObject 먼저)
7. 들여쓰기 및 문법
8. 함수 호출 포함
```

## 🚀 사용 방법

### 기본 사용법 (LLM Critic 활성화)
```bash
python3 scripts/run_llm.py --floor-plan 6 --model gpt-3.5-turbo
```

### LLM Critic 모델 지정
```bash
python3 scripts/run_llm.py --floor-plan 6 --model gpt-3.5-turbo --critic-model ollama:llama3
```

### LLM Critic 비활성화
```bash
python3 scripts/run_llm.py --floor-plan 6 --model gpt-3.5-turbo --disable-critic
```

## ⚙️ 설정 옵션

### `--critic-model`
- **기본값**: `ollama:llama3`
- **설명**: LLM Critic에 사용할 모델
- **지원 모델**: 
  - `ollama:llama3` (로컬, 빠름)
  - `ollama:tinyllama` (로컬, 매우 빠름)
  - `gpt-3.5-turbo` (클라우드, 정확함)
  - `gpt-4` (클라우드, 매우 정확함)

### `--disable-critic`
- **기본값**: False (활성화됨)
- **설명**: LLM Critic 검증을 비활성화
- **사용 시**: `--disable-critic` 플래그 추가

## 📊 작동 과정

```
1. 코드 생성 (기본 LLM)
   ↓
2. 코드 정리 (clean_generated_code)
   ↓
3. LLM Critic 검증
   ├─ 문제 없음 → 원본 코드 사용
   └─ 문제 발견 → 수정된 코드 생성
       ↓
       추가 코드 정리 (clean_generated_code)
   ↓
4. 최종 코드 저장
```

## 💡 사용 예시

### 예시 1: 기본 사용
```bash
cd /home/junghanbee/바탕화면/hanbee/SMART-LLM-master/SMART-LLM
python3 scripts/run_llm.py --floor-plan 6 --model gpt-3.5-turbo
```

**출력 예시:**
```
선택된 모델: gpt-3.5-turbo
LLM Critic 모델: ollama:llama3

🔍 Task 1/1 분해 중: Wash the lettuce and place lettuce on the Countertop
✅ Task 1 분해 완료!

🔍 Task 1/1 LLM Critic 검증 중...
🤖 Critic 모델: ollama:llama3
✅ LLM Critic 검증 통과: 코드가 올바르게 생성되었습니다.
✅ Task 1 코드가 검증을 통과했습니다.
```

### 예시 2: 다른 Critic 모델 사용
```bash
python3 scripts/run_llm.py --floor-plan 6 --model gpt-3.5-turbo --critic-model gpt-4
```

### 예시 3: Critic 비활성화 (빠른 실행)
```bash
python3 scripts/run_llm.py --floor-plan 6 --model gpt-3.5-turbo --disable-critic
```

## 🔧 문제 해결

### 1. **Critic 모델이 느린 경우**
```bash
# 더 빠른 모델 사용
python3 scripts/run_llm.py --floor-plan 6 --model gpt-3.5-turbo --critic-model ollama:tinyllama
```

### 2. **Critic이 계속 오류를 수정하는 경우**
- Critic 모델을 더 정확한 것으로 변경
- 또는 `--disable-critic`으로 비활성화

### 3. **API 키 오류**
- Critic 모델에 맞는 API 키를 올바르게 입력
- Ollama 모델은 API 키 불필요

## 📈 성능 비교

| 설정 | 속도 | 정확도 | 비용 |
|------|------|--------|------|
| Critic 없음 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| ollama:tinyllama | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| ollama:llama3 | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| gpt-3.5-turbo | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| gpt-4 | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |

## 🎯 권장 설정

### **개발/테스트용**
```bash
python3 scripts/run_llm.py --floor-plan 6 --model gpt-3.5-turbo --critic-model ollama:tinyllama
```

### **프로덕션용**
```bash
python3 scripts/run_llm.py --floor-plan 6 --model gpt-4 --critic-model gpt-3.5-turbo
```

### **빠른 실행**
```bash
python3 scripts/run_llm.py --floor-plan 6 --model gpt-3.5-turbo --disable-critic
```

## 🔍 로그 확인

생성된 로그에서 LLM Critic의 작동을 확인할 수 있습니다:
- `log.txt`: 전체 실행 과정
- `executable_plan.py`: 최종 검증된 코드

LLM Critic으로 더욱 안정적이고 정확한 코드를 생성하세요! 🎉
