import math
import re
import shutil
import subprocess
import time
import threading
import cv2
import numpy as np
from ai2thor.controller import Controller
from scipy.spatial import distance
from typing import Tuple
from collections import deque
import random
import os
from glob import glob

def closest_node(node, nodes, no_robot, clost_node_location):
    crps = []
    distances = distance.cdist([node], nodes)[0]
    dist_indices = np.argsort(np.array(distances))
    for i in range(no_robot):
        pos_index = dist_indices[(i * 5) + clost_node_location[i]]
        crps.append (nodes[pos_index])
    return crps

def distance_pts(p1: Tuple[float, float, float], p2: Tuple[float, float, float]):
    return ((p1[0] - p2[0]) ** 2 + (p1[2] - p2[2]) ** 2) ** 0.5

def generate_video():
    # 이미지 저장 기능이 제거되어 개별 비디오 생성 비활성화
    print("개별 비디오 생성 기능이 비활성화되었습니다. 통합 비디오만 생성됩니다.")
    pass
        



robots = [{'name': 'robot1', 'skills': ['GoToObject', 'SwitchOn', 'SwitchOff'], 'mass': 100}, {'name': 'robot2', 'skills': ['GoToObject', 'PickupObject', 'PutObject'], 'mass': 100}, {'name': 'robot3', 'skills': ['GoToObject', 'SliceObject', 'PickupObject'], 'mass': 100}]

floor_no = 21


ground_truth = [{'name': 'Toaster', 'contains': ['BreadSliced'], 'state': 'ON'}]
no_trans_gt = 0
max_trans = 1

import numpy as np
import time

total_exec = 0
success_exec = 0

# 비디오 라이터 초기화
video_writer = None
video_initialized = False

c = Controller( height=600, width=600)
c.reset("FloorPlan" + str(floor_no)) 
no_robot = len(robots)

# initialize n agents into the scene
multi_agent_event = c.step(dict(action='Initialize', agentMode="default", snapGrid=False, gridSize=0.5, rotateStepDegrees=20, visibilityDistance=100, fieldOfView=90, agentCount=no_robot))

# add a top view camera
event = c.step(action="GetMapViewCameraProperties")
event = c.step(action="AddThirdPartyCamera", **event.metadata["actionReturn"])

# get reachabel positions
reachable_positions_ = c.step(action="GetReachablePositions").metadata["actionReturn"]
reachable_positions = positions_tuple = [(p["x"], p["y"], p["z"]) for p in reachable_positions_]

# 환경에 맞는 최적 로봇 배치
def find_optimal_robot_positions(num_robots, reachable_positions):
    """로봇들을 적절히 떨어뜨려서 장애물이 없는 공간에 배치"""
    import math
    
    # 사용 가능한 위치들을 거리순으로 정렬 (중앙에서 가까운 순)
    center = (0, 0.9, 0)  # 중앙 기준점
    sorted_positions = sorted(reachable_positions, 
                            key=lambda pos: math.sqrt((pos['x'] - center[0])**2 + (pos['z'] - center[2])**2))
    
    selected_positions = []
    min_distance = 1.5  # 로봇 간 최소 거리 (미터)
    
    for pos in sorted_positions:
        # 이미 선택된 위치들과 충분히 떨어져 있는지 확인
        too_close = False
        for selected in selected_positions:
            distance = math.sqrt((pos['x'] - selected['x'])**2 + (pos['z'] - selected['z'])**2)
            if distance < min_distance:
                too_close = True
                break
        
        if not too_close:
            selected_positions.append(pos)
            if len(selected_positions) >= num_robots:
                break
    
    # 필요한 만큼 위치가 없으면 추가로 무작위 선택
    while len(selected_positions) < num_robots:
        remaining_positions = [p for p in reachable_positions if p not in selected_positions]
        if remaining_positions:
            selected_positions.append(random.choice(remaining_positions))
        else:
            break
    
    return selected_positions

# 최적 위치 계산
optimal_positions = find_optimal_robot_positions(no_robot, reachable_positions_)

for i in range(no_robot):
    if i < len(optimal_positions):
        init_pos = optimal_positions[i]
    else:
        # 예비 위치가 부족하면 무작위 선택
        init_pos = random.choice(reachable_positions_)
    
    c.step(dict(action="Teleport", position=init_pos, agentId=i))
    print(f"🤖 로봇 {i} 초기 위치: ({init_pos['x']:.1f}, {init_pos['y']:.1f}, {init_pos['z']:.1f})")
    
objs = list([obj["objectId"] for obj in c.last_event.metadata["objects"]])
# print (objs)
    
# x = c.step(dict(action="RemoveFromScene", objectId='Lettuce|+01.11|+00.83|-01.43'))
#c.step({"action":"InitialRandomSpawn", "excludedReceptacles":["Microwave", "Pan", "Chair", "Plate", "Fridge", "Cabinet", "Drawer", "GarbageCan"]})
# c.step({"action":"InitialRandomSpawn", "excludedReceptacles":["Cabinet", "Drawer", "GarbageCan"]})

action_queue = []

task_over = False

recp_id = None

# 경로 충돌 감지 및 회피 시스템
robot_positions = {}  # 로봇들의 현재 위치 저장
robot_targets = {}    # 로봇들의 목표 위치 저장
collision_threshold = 1.5  # 충돌 감지 거리 (미터)
avoidance_attempts = {}  # 로봇별 회피 시도 횟수
max_avoidance_attempts = 3  # 최대 회피 시도 횟수

for i in range (no_robot):
    multi_agent_event = c.step(action="LookDown", degrees=35, agentId=i)
    # c.step(action="LookUp", degrees=30, 'agent_id':i)

# 회피 관련 함수들
def get_robot_position(agent_id):
    """로봇의 현재 위치를 반환"""
    try:
        metadata = c.last_event.events[agent_id].metadata
        return (metadata['agent']['position']['x'], 
                metadata['agent']['position']['y'], 
                metadata['agent']['position']['z'])
    except:
        return None

def calculate_distance(pos1, pos2):
    """두 위치 간의 거리 계산"""
    if pos1 is None or pos2 is None:
        return float('inf')
    return np.sqrt(sum((a - b) ** 2 for a, b in zip(pos1, pos2)))

def detect_immediate_collision(moving_robot_id, target_position):
    """즉시 충돌 감지 - 바로 앞에서 막고 있는 로봇만 찾기"""
    moving_pos = get_robot_position(moving_robot_id)
    if moving_pos is None:
        return None
    
    # 이동 방향 벡터 계산
    direction_vector = np.array([
        target_position[0] - moving_pos[0],
        target_position[2] - moving_pos[2]  # Y는 무시하고 X, Z만 고려
    ])
    
    # 방향 벡터 정규화
    if np.linalg.norm(direction_vector) == 0:
        return None
    direction_vector = direction_vector / np.linalg.norm(direction_vector)
    
    # 다른 로봇들과의 거리 확인
    for other_robot_id in range(no_robot):
        if other_robot_id == moving_robot_id:
            continue
            
        other_pos = get_robot_position(other_robot_id)
        if other_pos is None:
            continue
        
        # 다른 로봇과의 거리
        distance_to_other = calculate_distance(moving_pos, other_pos)
        
        # 바로 앞에 있는지 확인 (1.5미터 이내)
        if distance_to_other > collision_threshold:
            continue
            
        # 다른 로봇이 이동 방향 앞에 있는지 확인
        to_other_vector = np.array([
            other_pos[0] - moving_pos[0],
            other_pos[2] - moving_pos[2]
        ])
        
        # 내적을 통해 앞쪽에 있는지 확인
        dot_product = np.dot(direction_vector, to_other_vector)
        
        # 앞쪽에 있고 충분히 가까이 있으면 막고 있는 것으로 판단
        if dot_product > 0 and distance_to_other < 1.0:  # 1미터 이내에서 앞쪽
            return other_robot_id
    
    return None

def find_avoidance_position(blocking_robot_id, moving_robot_id, target_position):
    """회피 위치 찾기 - 막고 있는 로봇을 1.5미터 옆으로 이동"""
    blocking_pos = get_robot_position(blocking_robot_id)
    if blocking_pos is None:
        return None
    
    # 막고 있는 로봇을 목표 위치에서 1.5미터 옆으로 이동시키기
    dx = target_position[0] - blocking_pos[0]
    dz = target_position[2] - blocking_pos[2]
    
    # 1.0미터 거리로 이동 (더 가까운 거리로 확실한 회피)
    avoidance_distance = 1.0
    
    # 여러 방향으로 회피 위치 시도
    avoidance_candidates = []
    
    if abs(dx) > abs(dz):
        # X 방향으로 이동
        if dx > 0:
            avoidance_candidates.append((blocking_pos[0] - avoidance_distance, blocking_pos[1], blocking_pos[2]))
            avoidance_candidates.append((blocking_pos[0] - avoidance_distance, blocking_pos[1], blocking_pos[2] + 0.5))
            avoidance_candidates.append((blocking_pos[0] - avoidance_distance, blocking_pos[1], blocking_pos[2] - 0.5))
        else:
            avoidance_candidates.append((blocking_pos[0] + avoidance_distance, blocking_pos[1], blocking_pos[2]))
            avoidance_candidates.append((blocking_pos[0] + avoidance_distance, blocking_pos[1], blocking_pos[2] + 0.5))
            avoidance_candidates.append((blocking_pos[0] + avoidance_distance, blocking_pos[1], blocking_pos[2] - 0.5))
    else:
        # Z 방향으로 이동
        if dz > 0:
            avoidance_candidates.append((blocking_pos[0], blocking_pos[1], blocking_pos[2] - avoidance_distance))
            avoidance_candidates.append((blocking_pos[0] + 0.5, blocking_pos[1], blocking_pos[2] - avoidance_distance))
            avoidance_candidates.append((blocking_pos[0] - 0.5, blocking_pos[1], blocking_pos[2] - avoidance_distance))
        else:
            avoidance_candidates.append((blocking_pos[0], blocking_pos[1], blocking_pos[2] + avoidance_distance))
            avoidance_candidates.append((blocking_pos[0] + 0.5, blocking_pos[1], blocking_pos[2] + avoidance_distance))
            avoidance_candidates.append((blocking_pos[0] - 0.5, blocking_pos[1], blocking_pos[2] + avoidance_distance))
    
    # 가장 가까운 유효한 위치 찾기
    for candidate in avoidance_candidates:
        # reachable_positions에서 가장 가까운 위치 찾기
        min_distance = float('inf')
        best_position = None
        
        for reachable_pos in reachable_positions:
            distance = calculate_distance(candidate, reachable_pos)
            if distance < min_distance and distance < 0.5:  # 0.5미터 이내의 유효한 위치
                min_distance = distance
                best_position = reachable_pos
        
        if best_position is not None:
            return best_position
    
    # 모든 후보가 실패하면 현재 위치에서 1미터 떨어진 곳으로 이동
    return (blocking_pos[0] + 1.0, blocking_pos[1], blocking_pos[2])

def execute_collision_avoidance(blocking_robot_id, avoidance_position):
    """충돌 회피 실행 - 막고 있는 로봇을 옆으로 이동"""
    print(f"🔄 로봇 {blocking_robot_id}이 경로를 열기 위해 {avoidance_position}로 이동합니다.")
    
    # 막고 있는 로봇을 회피 위치로 연속적으로 이동 (ObjectNavExpertAction 사용)
    action_queue.append({
        'action': 'ObjectNavExpertAction',
        'position': dict(x=avoidance_position[0], y=avoidance_position[1], z=avoidance_position[2]),
        'agent_id': blocking_robot_id
    })
    
    # 회피 완료까지 충분한 시간 대기 (더 긴 시간으로 확실한 이동 보장)
    time.sleep(5.0)

def exec_actions():
    global total_exec, success_exec, video_writer, video_initialized
    # delete if current output already exist
    cur_path = os.path.dirname(__file__) + "/*/"
    for x in glob(cur_path, recursive = True):
        shutil.rmtree (x)
    
    # 이미지 저장 기능 제거로 폴더 생성 불필요
    # for i in range(no_robot):
    #     folder_name = "agent_" + str(i+1)
    #     folder_path = os.path.dirname(__file__) + "/" + folder_name
    #     if not os.path.exists(folder_path):
    #         os.makedirs(folder_path)
    
    # folder_name = "top_view"
    # folder_path = os.path.dirname(__file__) + "/" + folder_name
    # if not os.path.exists(folder_path):
    #     os.makedirs(folder_path)
    
    img_counter = 0
    
    while not task_over:
        if len(action_queue) > 0:
            try:
                act = action_queue[0]
                if act['action'] == 'ObjectNavExpertAction':
                    multi_agent_event = c.step(dict(action=act['action'], position=act['position'], agentId=act['agent_id']))
                    next_action = multi_agent_event.metadata['actionReturn']

                    if next_action != None:
                        multi_agent_event = c.step(action=next_action, agentId=act['agent_id'], forceAction=True)
                
                elif act['action'] == 'MoveAhead':
                    multi_agent_event = c.step(action="MoveAhead", agentId=act['agent_id'])
                    
                elif act['action'] == 'MoveBack':
                    multi_agent_event = c.step(action="MoveBack", agentId=act['agent_id'])
                        
                elif act['action'] == 'RotateLeft':
                    multi_agent_event = c.step(action="RotateLeft", degrees=act['degrees'], agentId=act['agent_id'])
                    
                elif act['action'] == 'RotateRight':
                    multi_agent_event = c.step(action="RotateRight", degrees=act['degrees'], agentId=act['agent_id'])
                    
                elif act['action'] == 'PickupObject':
                    total_exec += 1
                    multi_agent_event = c.step(action="PickupObject", objectId=act['objectId'], agentId=act['agent_id'], forceAction=True)
                    if multi_agent_event.metadata['errorMessage'] != "":
                        print (multi_agent_event.metadata['errorMessage'])
                    else:
                        success_exec += 1
 
                elif act['action'] == 'PutObject':
                    total_exec += 1
                    multi_agent_event = c.step(action="PutObject", agentId=act['agent_id'], forceAction=True)
                    if multi_agent_event.metadata['errorMessage'] != "":
                        print (multi_agent_event.metadata['errorMessage'])
                    else:
                        success_exec += 1
 
                elif act['action'] == 'ToggleObjectOn':
                    total_exec += 1
                    multi_agent_event = c.step(action="ToggleObjectOn", objectId=act['objectId'], agentId=act['agent_id'], forceAction=True)
                    if multi_agent_event.metadata['errorMessage'] != "":
                        print (multi_agent_event.metadata['errorMessage'])
                    else:
                        success_exec += 1
                
                elif act['action'] == 'ToggleObjectOff':
                    total_exec += 1
                    multi_agent_event = c.step(action="ToggleObjectOff", objectId=act['objectId'], agentId=act['agent_id'], forceAction=True)
                    if multi_agent_event.metadata['errorMessage'] != "":
                        print (multi_agent_event.metadata['errorMessage'])
                    else:
                        success_exec += 1
                    
                elif act['action'] == 'OpenObject':
                    total_exec += 1
                    multi_agent_event = c.step(action="OpenObject", objectId=act['objectId'], agentId=act['agent_id'], forceAction=True)
                    if multi_agent_event.metadata['errorMessage'] != "":
                        print (multi_agent_event.metadata['errorMessage'])
                    else:
                        success_exec += 1
 
                    
                elif act['action'] == 'CloseObject':
                    total_exec += 1
                    multi_agent_event = c.step(action="CloseObject", objectId=act['objectId'], agentId=act['agent_id'], forceAction=True)
                    if multi_agent_event.metadata['errorMessage'] != "":
                        print (multi_agent_event.metadata['errorMessage'])
                    else:
                        success_exec += 1
                        
                elif act['action'] == 'SliceObject':
                    total_exec += 1
                    multi_agent_event = c.step(action="SliceObject", objectId=act['objectId'], agentId=act['agent_id'], forceAction=True)
                    if multi_agent_event.metadata['errorMessage'] != "":
                        print (multi_agent_event.metadata['errorMessage'])
                    else:
                        success_exec += 1
                        
                elif act['action'] == 'ThrowObject':
                    total_exec += 1
                    multi_agent_event = c.step(action="ThrowObject", moveMagnitude=7, agentId=act['agent_id'], forceAction=True)
                    if multi_agent_event.metadata['errorMessage'] != "":
                        print (multi_agent_event.metadata['errorMessage'])
                    else:
                        success_exec += 1
                        
                elif act['action'] == 'BreakObject':
                    total_exec += 1
                    multi_agent_event = c.step(action="BreakObject", objectId=act['objectId'], agentId=act['agent_id'], forceAction=True)
                    if multi_agent_event.metadata['errorMessage'] != "":
                        print (multi_agent_event.metadata['errorMessage'])
                    else:
                        success_exec += 1
                
                elif act['action'] == 'ToggleObjectOn':
                    total_exec += 1
                    multi_agent_event = c.step(action="ToggleObjectOn", objectId=act['objectId'], agentId=act['agent_id'])
                    if multi_agent_event.metadata['errorMessage'] != "":
                        print(f"❌ ToggleObjectOn 실패: {multi_agent_event.metadata['errorMessage']}")
                    else:
                        print(f"✅ ToggleObjectOn 성공: {act['objectId']}가 켜졌습니다.")
                        success_exec += 1
                
                elif act['action'] == 'Teleport':
                    total_exec += 1
                    multi_agent_event = c.step(action="Teleport", position=dict(x=act['x'], y=act['y'], z=act['z']), agentId=act['agent_id'])
                    if multi_agent_event.metadata['errorMessage'] != "":
                        print(f"❌ Teleport 실패: {multi_agent_event.metadata['errorMessage']}")
                    else:
                        print(f"✅ Teleport 성공: 로봇 {act['agent_id']}이 ({act['x']:.1f}, {act['y']:.1f}, {act['z']:.1f})로 이동했습니다.")
                        success_exec += 1
 
                
                elif act['action'] == 'Done':
                    multi_agent_event = c.step(action="Done")
                    
                    
            except Exception as e:
                print (e)
                
            # 각 에이전트 이미지 수집 (저장하지 않음)
            agent_images = []
            for i,e in enumerate(multi_agent_event.events):
                agent_images.append(e.cv2img)
            
            # Top view 이미지 수집 (저장하지 않음)
            top_view_rgb = cv2.cvtColor(c.last_event.events[0].third_party_camera_frames[-1], cv2.COLOR_BGR2RGB)
            
            # 모든 시각화를 하나의 창에 분할로 표시
            if agent_images:
                num_agents = len(agent_images)
                h, w = agent_images[0].shape[:2]
                
                # 모든 로봇 수에 대해 3x2 그리드로 통일
                combined = np.zeros((h*2, w*3, 3), dtype=np.uint8)
                
                # 에이전트 이미지 배치 (최대 6개)
                positions = [
                    (0, 0), (0, w), (0, 2*w),      # 첫 번째 행
                    (h, 0), (h, w), (h, 2*w)        # 두 번째 행
                ]
                
                for i, (y, x) in enumerate(positions):
                    if i < len(agent_images):
                        combined[y:y+h, x:x+w] = agent_images[i]
                        cv2.putText(combined, f"Agent {i+1}", (x+10, y+30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                    elif i == len(agent_images) and len(agent_images) < 6:
                        # 마지막 위치에 Top View 배치
                        combined[y:y+h, x:x+w] = top_view_rgb
                        cv2.putText(combined, "Top View", (x+10, y+30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                        break
                    else:
                        # 빈 공간
                        combined[y:y+h, x:x+w] = np.zeros((h, w, 3), dtype=np.uint8)
                
                cv2.imshow('SMART-LLM Multi-Agent View', combined)
                
                # 통합 화면을 비디오로 저장
                if not video_initialized:
                    try:
                        # 현재 로그 폴더 경로 찾기 (glob 모듈 충돌 방지)
                        import glob as glob_module
                        log_folders = glob_module.glob(os.path.join(os.getcwd(), "logs", "*"))
                        latest_log_folder = max(log_folders, key=os.path.getctime) if log_folders else os.getcwd()
                        
                        # 비디오 파일 경로 설정 (로그 폴더 내)
                        video_path = os.path.join(latest_log_folder, "combined_visualization.mp4")
                        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                        fps = 25
                        video_writer = cv2.VideoWriter(video_path, fourcc, fps, (combined.shape[1], combined.shape[0]))
                        video_initialized = True
                        print(f"비디오 저장 시작: {video_path}")
                    except Exception as e:
                        print(f"비디오 라이터 초기화 실패: {e}")
                
                if video_writer is not None:
                    video_writer.write(combined)
            
            if cv2.waitKey(25) & 0xFF == ord('q'):
                break
            
            img_counter += 1    
            action_queue.pop(0)
       
actions_thread = threading.Thread(target=exec_actions)
actions_thread.start()

def GoToObject(robots, dest_obj):
    global recp_id
    
    # check if robots is a list
    
    if not isinstance(robots, list):
        # convert robot to a list
        robots = [robots]
    no_agents = len (robots)
    # robots distance to the goal 
    dist_goals = [10.0] * len(robots)
    prev_dist_goals = [10.0] * len(robots)
    count_since_update = [0] * len(robots)
    clost_node_location = [0] * len(robots)
    
    # list of objects in the scene and their centers
    objs = list([obj["objectId"] for obj in c.last_event.metadata["objects"]])
    objs_center = list([obj["axisAlignedBoundingBox"]["center"] for obj in c.last_event.metadata["objects"]])
    if "|" in dest_obj:
        # obj alredy given
        dest_obj_id = dest_obj
        pos_arr = dest_obj_id.split("|")
        dest_obj_center = {'x': float(pos_arr[1]), 'y': float(pos_arr[2]), 'z': float(pos_arr[3])}
    else:
        dest_obj_id = None
        dest_obj_center = None
        min_distance = float('inf')
        
        # 여러 개의 같은 타입 객체가 있을 때 가장 가까운 것 선택
        for idx, obj in enumerate(objs):
            match = re.match(dest_obj, obj)
            if match is not None:
                obj_center = objs_center[idx]
                if obj_center != {'x': 0.0, 'y': 0.0, 'z': 0.0}:
                    # 로봇과의 거리 계산 (첫 번째 로봇 기준)
                    if len(robots) > 0:
                        robot_name = robots[0]['name']
                        agent_id = int(robot_name[-1]) - 1
                        try:
                            metadata = c.last_event.events[agent_id].metadata
                            robot_pos = [
                                metadata["agent"]["position"]["x"],
                                metadata["agent"]["position"]["y"], 
                                metadata["agent"]["position"]["z"]
                            ]
                            distance = ((robot_pos[0] - obj_center['x'])**2 + 
                                      (robot_pos[1] - obj_center['y'])**2 + 
                                      (robot_pos[2] - obj_center['z'])**2)**0.5
                            
                            if distance < min_distance:
                                min_distance = distance
                                dest_obj_id = obj
                                dest_obj_center = obj_center
                        except:
                            # 로봇 위치를 가져올 수 없으면 첫 번째 유효한 객체 선택
                            if dest_obj_id is None:
                                dest_obj_id = obj
                                dest_obj_center = obj_center
                    else:
                        # 로봇이 없으면 첫 번째 유효한 객체 선택
                        if dest_obj_id is None:
                            dest_obj_id = obj
                            dest_obj_center = obj_center
        
        # 객체를 찾지 못한 경우 오류 처리
        if dest_obj_id is None:
            print(f"오류: '{dest_obj}' 객체를 찾을 수 없습니다.")
            print(f"사용 가능한 객체들: {objs[:10]}...")  # 처음 10개만 표시
            return
        
    print ("Going to ", dest_obj_id, dest_obj_center)
        
    dest_obj_pos = [dest_obj_center['x'], dest_obj_center['y'], dest_obj_center['z']] 
    
    # closest reachable position for each robot
    # all robots cannot reach the same spot 
    # differt close points needs to be found for each robot
    crp = closest_node(dest_obj_pos, reachable_positions, no_agents, clost_node_location)
    
    goal_thresh = 0.25
    # at least one robot is far away from the goal
    
    while all(d > goal_thresh for d in dist_goals):
        for ia, robot in enumerate(robots):
            robot_name = robot['name']
            agent_id = int(robot_name[-1]) - 1
            
            # get the pose of robot        
            metadata = c.last_event.events[agent_id].metadata
            location = {
                "x": metadata["agent"]["position"]["x"],
                "y": metadata["agent"]["position"]["y"],
                "z": metadata["agent"]["position"]["z"],
                "rotation": metadata["agent"]["rotation"]["y"],
                "horizon": metadata["agent"]["cameraHorizon"]}
            
            prev_dist_goals[ia] = dist_goals[ia] # store the previous distance to goal
            dist_goals[ia] = distance_pts([location['x'], location['y'], location['z']], crp[ia])
            
            dist_del = abs(dist_goals[ia] - prev_dist_goals[ia])
            # print (ia, "Dist to Goal: ", dist_goals[ia], dist_del, clost_node_location[ia])
            if dist_del < 0.2:
                # robot did not move 
                count_since_update[ia] += 1
            else:
                # robot moving 
                count_since_update[ia] = 0
                
            if count_since_update[ia] < 8:
                # 회피 시스템 비활성화 - 로봇들이 서로를 막지 않도록 함
                # 대신 각 로봇이 독립적으로 경로를 찾도록 함
                action_queue.append({'action':'ObjectNavExpertAction', 'position':dict(x=crp[ia][0], y=crp[ia][1], z=crp[ia][2]), 'agent_id':agent_id})
            else:    
                #updating goal
                clost_node_location[ia] += 1
                count_since_update[ia] = 0
                crp = closest_node(dest_obj_pos, reachable_positions, no_agents, clost_node_location)
    
            time.sleep(0.5)

    # align the robot once goal is reached
    # compute angle between robot heading and object
    metadata = c.last_event.events[agent_id].metadata
    robot_location = {
        "x": metadata["agent"]["position"]["x"],
        "y": metadata["agent"]["position"]["y"],
        "z": metadata["agent"]["position"]["z"],
        "rotation": metadata["agent"]["rotation"]["y"],
        "horizon": metadata["agent"]["cameraHorizon"]}
    
    robot_object_vec = [dest_obj_pos[0] -robot_location['x'], dest_obj_pos[2]-robot_location['z']]
    y_axis = [0, 1]
    unit_y = y_axis / np.linalg.norm(y_axis)
    unit_vector = robot_object_vec / np.linalg.norm(robot_object_vec)
    
    angle = math.atan2(np.linalg.det([unit_vector,unit_y]),np.dot(unit_vector,unit_y))
    angle = 360*angle/(2*np.pi)
    angle = (angle + 360) % 360
    rot_angle = angle - robot_location['rotation']
    
    if rot_angle > 0:
        action_queue.append({'action':'RotateRight', 'degrees':abs(rot_angle), 'agent_id':agent_id})
    else:
        action_queue.append({'action':'RotateLeft', 'degrees':abs(rot_angle), 'agent_id':agent_id})
        
    print ("Reached: ", dest_obj)
    if dest_obj == "Cabinet" or dest_obj == "Fridge" or dest_obj == "CounterTop" or dest_obj == "Drawer":
        recp_id = dest_obj_id
        print(f"🔗 선택된 {dest_obj}가 모든 로봇에게 공유됩니다: {dest_obj_id}")
    
def PickupObject(robots, pick_obj):
    if not isinstance(robots, list):
        # convert robot to a list
        robots = [robots]
    no_agents = len (robots)
    # robots distance to the goal 
    for idx in range(no_agents):
        robot = robots[idx]
        print ("PIcking: ", pick_obj)
        robot_name = robot['name']
        agent_id = int(robot_name[-1]) - 1
        # list of objects in the scene and their centers
        objs = list([obj["objectId"] for obj in c.last_event.metadata["objects"]])
        objs_center = list([obj["axisAlignedBoundingBox"]["center"] for obj in c.last_event.metadata["objects"]])
        objs_metadata = c.last_event.metadata["objects"]
        
        pick_obj_id = None
        dest_obj_center = None
        pick_obj_metadata = None
        
        for idx, obj in enumerate(objs):
            # 정확한 매치 또는 패턴 매치 (문자열 어느 부분에서든)
            if obj == pick_obj or re.search(pick_obj, obj):
                pick_obj_id = obj
                dest_obj_center = objs_center[idx]
                pick_obj_metadata = objs_metadata[idx]
                if dest_obj_center != {'x': 0.0, 'y': 0.0, 'z': 0.0}:
                    break # find the first instance
        
        if pick_obj_id is None:
            print(f"❌ 객체를 찾을 수 없습니다: {pick_obj}")
            print("🔍 사용 가능한 객체들:")
            for obj in objs:
                print(f"  - {obj}")
            return
        
        # 객체가 집을 수 있는지 확인
        if pick_obj_metadata and not pick_obj_metadata.get('pickupable', True):
            print(f"❌ {pick_obj}는 집을 수 없는 객체입니다.")
            return
            
        # GoToObject(robot, pick_obj_id)
        # time.sleep(1)
        print ("Picking Up ", pick_obj_id, dest_obj_center)
        action_queue.append({'action':'PickupObject', 'objectId':pick_obj_id, 'agent_id':agent_id})
        time.sleep(1)
    
def PutObject(robot, recp):
    robot_name = robot['name']
    agent_id = int(robot_name[-1]) - 1
    objs = list(set([obj["objectId"] for obj in c.last_event.metadata["objects"]]))
    objs_center = list([obj["axisAlignedBoundingBox"]["center"] for obj in c.last_event.metadata["objects"]])
    objs_dists = list([obj["distance"] for obj in c.last_event.metadata["objects"]])

    metadata = c.last_event.events[agent_id].metadata
    robot_location = [metadata["agent"]["position"]["x"], metadata["agent"]["position"]["y"], metadata["agent"]["position"]["z"]]
    dist_to_recp = 9999999 # distance b/w robot and the recp obj
    for idx, obj in enumerate(objs):
        match = re.match(recp, obj)
        if match is not None:
            dist = objs_dists[idx]
            if dist < dist_to_recp:
                recp_obj_id = obj
                dest_obj_center = objs_center[idx]
                dist_to_recp = dist
                
    
    global recp_id         
    if recp_id is not None:
        recp_obj_id = recp_id
        print(f"🔗 공유된 {recp} 사용: {recp_obj_id}")
    # GoToObject(robot, recp_obj_id)
    # time.sleep(1)
    
    # 수신기 타입에 따른 처리 - AI2THOR 메타데이터를 동적으로 활용
    recp_obj_metadata = None
    for obj in c.last_event.metadata["objects"]:
        if re.match(recp, obj["objectId"]):
            recp_obj_metadata = obj
            break
    
    if recp_obj_metadata is None:
        print(f"❌ 수신기 객체를 찾을 수 없습니다: {recp}")
        return False
    
    # 메타데이터에서 객체 속성 확인
    is_openable = recp_obj_metadata.get('openable', False)
    is_pickupable = recp_obj_metadata.get('pickupable', False)
    is_toggleable = recp_obj_metadata.get('toggleable', False)
    
    # 항상 열려있는 객체들 (일반적으로 컨테이너가 아닌 표면)
    always_open_containers = ["CounterTop", "Table", "Shelf", "Floor", "Wall", "Bowl", "Plate", "Cup", "Mug","Toaster","TrashCan", "Box", "Bookcase"
    ,"TrashCan", "Desk"]
    is_always_open = any(container in recp for container in always_open_containers)
    
    if is_always_open:
        # 항상 열려있는 수신기인 경우 - 바로 배치 시도
        print(f"ℹ️ {recp}는 항상 열려있는 수신기입니다. 바로 배치를 시도합니다.")
    elif is_openable:
        # 열고 닫을 수 있는 수신기인 경우 - 열림 상태 확인 및 필요시 열기
        recp_is_open = recp_obj_metadata.get('isOpen', False)
        
        if not recp_is_open:
            print(f"🔓 {recp}가 닫혀있어서 열어야 합니다.")
            # 수신기를 열기
            open_result = c.step(action="OpenObject", objectId=recp_obj_id, agentId=agent_id)
            if open_result.metadata['errorMessage'] != "":
                print(f"❌ {recp} 열기 실패: {open_result.metadata['errorMessage']}")
                return False
            else:
                print(f"✅ {recp}를 성공적으로 열었습니다.")
                time.sleep(1.0)  # 열기 완료까지 대기
        else:
            print(f"✅ {recp}는 이미 열려있습니다.")
    else:
        # 열고 닫을 수 없는 수신기(테이블, 카운터 등)는 바로 진행
        print(f"ℹ️ {recp}는 열고 닫을 수 없는 수신기입니다. 바로 배치를 시도합니다.")
    
    # PutObject 액션 실행
    print(f"PutObject 시도: 손에 든 객체 -> {recp}")
    print(f"🔍 대상 객체 ID: {recp_obj_id}")
    
    # AI2THOR의 PutObject는 손에 든 객체를 지정된 위치에 배치
    # objectId는 배치할 대상 객체의 ID
    result = c.step(action="PutObject", objectId=recp_obj_id, agentId=agent_id)
    
    if result.metadata['errorMessage'] != "":
        print(f"❌ 실패: {recp}에 배치 실패 - {result.metadata['errorMessage']}")
        return False
    else:
        print(f"✅ 성공: 객체가 {recp}에 배치됨")
        return True
         
def SwitchOn(robot, sw_obj):
    print ("Switching On: ", sw_obj)
    robot_name = robot['name']
    agent_id = int(robot_name[-1]) - 1
    objs = list(set([obj["objectId"] for obj in c.last_event.metadata["objects"]]))
    
    # turn on all stove burner
    if sw_obj == "StoveKnob":
        for obj in objs:
            match = re.match(sw_obj, obj)
            if match is not None:
                sw_obj_id = obj
                GoToObject(robot, sw_obj_id)
                # time.sleep(1)
                action_queue.append({'action':'ToggleObjectOn', 'objectId':sw_obj_id, 'agent_id':agent_id})
                time.sleep(0.1)
    
    # all objects apart from Stove Burner
    else:
        for obj in objs:
            match = re.match(sw_obj, obj)
            if match is not None:
                sw_obj_id = obj
                break # find the first instance
        GoToObject(robot, sw_obj_id)
        time.sleep(1)
        action_queue.append({'action':'ToggleObjectOn', 'objectId':sw_obj_id, 'agent_id':agent_id})
        time.sleep(1)            
        
def SwitchOff(robot, sw_obj):
    print ("Switching Off: ", sw_obj)
    robot_name = robot['name']
    agent_id = int(robot_name[-1]) - 1
    objs = list(set([obj["objectId"] for obj in c.last_event.metadata["objects"]]))
    
    # turn on all stove burner
    if sw_obj == "StoveKnob":
        for obj in objs:
            match = re.match(sw_obj, obj)
            if match is not None:
                sw_obj_id = obj
                action_queue.append({'action':'ToggleObjectOff', 'objectId':sw_obj_id, 'agent_id':agent_id})
                time.sleep(0.1)
    
    # all objects apart from Stove Burner
    else:
        for obj in objs:
            match = re.match(sw_obj, obj)
            if match is not None:
                sw_obj_id = obj
                break # find the first instance
        GoToObject(robot, sw_obj_id)
        time.sleep(1)
        action_queue.append({'action':'ToggleObjectOff', 'objectId':sw_obj_id, 'agent_id':agent_id})
        time.sleep(1)      
    
def OpenObject(robot, sw_obj):
    robot_name = robot['name']
    agent_id = int(robot_name[-1]) - 1
    objs = list(set([obj["objectId"] for obj in c.last_event.metadata["objects"]]))
    
    for obj in objs:
        match = re.match(sw_obj, obj)
        if match is not None:
            sw_obj_id = obj
            break # find the first instance
        
    global recp_id
    if recp_id is not None:
        sw_obj_id = recp_id
    
    GoToObject(robot, sw_obj_id)
    time.sleep(1)
    
    # OpenObject 액션 실행
    print(f"OpenObject 시도: {sw_obj}")
    action_queue.append({'action':'OpenObject', 'objectId':sw_obj_id, 'agent_id':agent_id})
    time.sleep(1)
    
    # OpenObject 실행 후 상태 확인
    time.sleep(2)  # 액션 완료 대기
    
    # 객체가 실제로 열렸는지 확인
    try:
        for obj in c.last_event.metadata["objects"]:
            if re.match(sw_obj, obj["objectId"]):
                if "isOpen" in obj and obj["isOpen"]:
                    print(f"✅ 성공: {sw_obj}가 열림")
                    return True
                else:
                    print(f"❌ 실패: {sw_obj}가 열리지 않음")
                    return False
    except Exception as e:
        print(f"상태 확인 중 오류: {e}")
        return False
    
def CloseObject(robot, sw_obj):
    robot_name = robot['name']
    agent_id = int(robot_name[-1]) - 1
    objs = list(set([obj["objectId"] for obj in c.last_event.metadata["objects"]]))
    
    for obj in objs:
        match = re.match(sw_obj, obj)
        if match is not None:
            sw_obj_id = obj
            break # find the first instance
        
    global recp_id
    if recp_id is not None:
        sw_obj_id = recp_id
        
    GoToObject(robot, sw_obj_id)
    time.sleep(1)
    
    action_queue.append({'action':'CloseObject', 'objectId':sw_obj_id, 'agent_id':agent_id}) 
    
    if recp_id is not None:
        recp_id = None
    time.sleep(1)
    
def BreakObject(robot, sw_obj):
    robot_name = robot['name']
    agent_id = int(robot_name[-1]) - 1
    objs = list(set([obj["objectId"] for obj in c.last_event.metadata["objects"]]))
    
    for obj in objs:
        match = re.match(sw_obj, obj)
        if match is not None:
            sw_obj_id = obj
            break # find the first instance
    GoToObject(robot, sw_obj_id)
    time.sleep(1)
    action_queue.append({'action':'BreakObject', 'objectId':sw_obj_id, 'agent_id':agent_id}) 
    time.sleep(1)

def ToggleObjectOn(robot, toggle_obj):
    """객체를 켜는 함수"""
    
    robot_name = robot['name']
    agent_id = int(robot_name[-1]) - 1
    objs = list(set([obj["objectId"] for obj in c.last_event.metadata["objects"]]))
    objs_metadata = c.last_event.metadata["objects"]
    
    toggle_obj_id = None
    toggle_obj_metadata = None
    
    for idx, obj in enumerate(objs):
        match = re.match(toggle_obj, obj)
        if match is not None:
            toggle_obj_id = obj
            toggle_obj_metadata = objs_metadata[idx]
            break # find the first instance
    
    if toggle_obj_id is None:
        print(f"❌ 객체를 찾을 수 없습니다: {toggle_obj}")
        return
    
    # 객체가 토글 가능한지 확인
    if toggle_obj_metadata and not toggle_obj_metadata.get('toggleable', False):
        print(f"❌ {toggle_obj}는 토글할 수 없는 객체입니다.")
        return
    
    # 이미 켜져있는지 확인
    if toggle_obj_metadata and toggle_obj_metadata.get('isToggled', False):
        print(f"ℹ️ {toggle_obj}는 이미 켜져있습니다.")
        return
    
    GoToObject(robot, toggle_obj_id)
    time.sleep(1)
    print(f"Toggle On: {toggle_obj}")
    action_queue.append({'action':'ToggleObjectOn', 'objectId':toggle_obj_id, 'agent_id':agent_id})
    time.sleep(1)
    
    # ToggleObjectOn 액션 실행
    multi_agent_event = c.step(action="ToggleObjectOn", objectId=toggle_obj_id, agentId=agent_id)
    if multi_agent_event.metadata['errorMessage'] != "":
        print(f"❌ 실패: {toggle_obj} 켜기 실패 - {multi_agent_event.metadata['errorMessage']}")
    else:
        print(f"✅ 성공: {toggle_obj}가 켜졌습니다.")

def ToggleObject(robot, toggle_obj):
    """객체를 토글하는 함수 (켜기/끄기)"""
    robot_name = robot['name']
    agent_id = int(robot_name[-1]) - 1
    objs = list(set([obj["objectId"] for obj in c.last_event.metadata["objects"]]))
    objs_metadata = c.last_event.metadata["objects"]
    
    toggle_obj_id = None
    toggle_obj_metadata = None
    
    for idx, obj in enumerate(objs):
        match = re.match(toggle_obj, obj)
        if match is not None:
            toggle_obj_id = obj
            toggle_obj_metadata = objs_metadata[idx]
            break # find the first instance
    
    if toggle_obj_id is None:
        print(f"❌ 객체를 찾을 수 없습니다: {toggle_obj}")
        return False
    
    # 객체가 토글 가능한지 확인
    if toggle_obj_metadata and not toggle_obj_metadata.get('toggleable', False):
        print(f"❌ {toggle_obj}는 토글할 수 없는 객체입니다.")
        return False
    
    GoToObject(robot, toggle_obj_id)
    time.sleep(1)
    
    # 현재 상태 확인
    is_toggled = toggle_obj_metadata.get('isToggled', False)
    action_name = "ToggleObjectOff" if is_toggled else "ToggleObjectOn"
    status_text = "끄기" if is_toggled else "켜기"
    
    print(f"Toggle {status_text}: {toggle_obj}")
    result = c.step(action=action_name, objectId=toggle_obj_id, agentId=agent_id)
    
    if result.metadata['errorMessage'] != "":
        print(f"❌ 실패: {toggle_obj} {status_text} 실패 - {result.metadata['errorMessage']}")
        return False
    else:
        print(f"✅ 성공: {toggle_obj}가 {status_text}되었습니다.")
        return True
    
def SliceObject(robot, sw_obj):
    print ("Slicing: ", sw_obj)
    robot_name = robot['name']
    agent_id = int(robot_name[-1]) - 1
    objs = list(set([obj["objectId"] for obj in c.last_event.metadata["objects"]]))
    
    sw_obj_id = None
    for obj in objs:
        match = re.match(sw_obj, obj)
        if match is not None:
            sw_obj_id = obj
            break # find the first instance
    
    if sw_obj_id is None:
        print(f"❌ 객체를 찾을 수 없습니다: {sw_obj}")
        print("🔍 사용 가능한 객체들:")
        for obj in objs:
            print(f"  - {obj}")
        return
    
    GoToObject(robot, sw_obj_id)
    time.sleep(1)
    action_queue.append({'action':'SliceObject', 'objectId':sw_obj_id, 'agent_id':agent_id})      
    time.sleep(1)

def CookObject(robot, cook_obj):
    """객체를 요리하는 함수 (전자레인지나 스토브 버너에서)"""
    robot_name = robot['name']
    agent_id = int(robot_name[-1]) - 1
    objs = list(set([obj["objectId"] for obj in c.last_event.metadata["objects"]]))
    
    cook_obj_id = None
    for obj in objs:
        match = re.match(cook_obj, obj)
        if match is not None:
            cook_obj_id = obj
            break # find the first instance
    
    if cook_obj_id is None:
        print(f"❌ 객체를 찾을 수 없습니다: {cook_obj}")
        print("🔍 사용 가능한 객체들:")
        for obj in objs:
            print(f"  - {obj}")
        return False
    
    GoToObject(robot, cook_obj_id)
    time.sleep(1)
    
    # CookObject 액션 실행
    print(f"Cooking: {cook_obj}")
    result = c.step(action="CookObject", objectId=cook_obj_id, agentId=agent_id)
    
    if result.metadata['errorMessage'] != "":
        print(f"❌ {cook_obj} 요리 실패: {result.metadata['errorMessage']}")
        return False
    else:
        print(f"✅ {cook_obj}를 성공적으로 요리했습니다.")
        return True
    

def CleanObject(robot, sw_obj):
    robot_name = robot['name']
    agent_id = int(robot_name[-1]) - 1
    objs = list(set([obj["objectId"] for obj in c.last_event.metadata["objects"]]))

    for obj in objs:
        match = re.match(sw_obj, obj)
        if match is not None:
            sw_obj_id = obj
            break # find the first instance
    GoToObject(robot, sw_obj_id)
    time.sleep(1)
    action_queue.append({'action':'CleanObject', 'objectId':sw_obj_id, 'agent_id':agent_id}) 
    time.sleep(1)
    
def ThrowObject(robot, sw_obj):
    robot_name = robot['name']
    agent_id = int(robot_name[-1]) - 1
    objs = list(set([obj["objectId"] for obj in c.last_event.metadata["objects"]]))

    for obj in objs:
        match = re.match(sw_obj, obj)
        if match is not None:
            sw_obj_id = obj
            break # find the first instance
    
    action_queue.append({'action':'ThrowObject', 'objectId':sw_obj_id, 'agent_id':agent_id}) 
    time.sleep(1)

def FillObjectWithLiquid(robot, obj):
    print ("Filling with liquid: ", obj)
    robot_name = robot['name']
    agent_id = int(robot_name[-1]) - 1
    objs = list(set([obj["objectId"] for obj in c.last_event.metadata["objects"]]))
    
    for obj_id in objs:
        match = re.match(obj, obj_id)
        if match is not None:
            obj_id_found = obj_id
            break
    GoToObject(robot, obj_id_found)
    time.sleep(1)
    action_queue.append({'action':'FillObjectWithLiquid', 'objectId':obj_id_found, 'agent_id':agent_id})
    time.sleep(1)
def toast_breadloaf(robot_list):
    # robot_list = [robot1]
    # 0: Go to the Knife using robot1.
    GoToObject(robot_list[0], 'Knife')
    # 1: Pick up the Knife using robot1.
    PickupObject(robot_list[0], 'Knife')
    # 2: Go to the Breadloaf using robot1.
    GoToObject(robot_list[0], 'Bread')
    # 3: Slice the Breadloaf using robot1.
    SliceObject(robot_list[0], 'Bread')
    # 4: Put the Knife using robot1.
    DropHandObject(robot_list[0])
    # 5: Pick up the sliced Breadloaf using robot1.
    PickupObject(robot_list[0], 'BreadSliced_1')
    # 6: Go to the Toaster using robot1.
    GoToObject(robot_list[0], 'Toaster')
    # 7: Put the Bread in the Toaster using robot1.
    PutObject(robot_list[0], 'Toaster')
    # 8: Turn on the Toaster using robot1.
    ToggleObject(robot_list[0], 'Toaster')
    # 9: Pick up the toasted Breadloaf using robot1.
    PickupObject(robot_list[0], 'BreadSliced_1')

# Execute SubTask
toast_breadloaf([robots[0]])

no_trans = 0

for i in range(25):
    action_queue.append({'action':'Done'})
    action_queue.append({'action':'Done'})
    action_queue.append({'action':'Done'})
    time.sleep(0.1)

task_over = True
time.sleep(5)


if total_exec > 0:
    exec = float(success_exec) / float(total_exec)
else:
    exec = 0.0
    print("Warning: No actions were executed (total_exec = 0)")

print (ground_truth)
objs = list([obj for obj in c.last_event.metadata["objects"]])

gcr_tasks = 0.0
gcr_complete = 0.0
for obj_gt in ground_truth:
    obj_name = obj_gt['name']
    state = obj_gt['state']
    contains = obj_gt['contains']
    gcr_tasks += 1
    for obj in objs:
        # if obj_name in obj["name"]:
        #     print (obj)
        if state == 'SLICED':
            if obj_name in obj["name"] and obj["isSliced"]:
                gcr_complete += 1 
                
        if state == 'OFF':
            if obj_name in obj["name"] and not obj["isToggled"]:
                gcr_complete += 1 
        
        if state == 'ON':
            if obj_name in obj["name"] and obj["isToggled"]:
                gcr_complete += 1 
        
        if state == 'HOT':
            # print (obj)
            if obj_name in obj["name"] and obj["temperature"] == 'Hot':
                gcr_complete += 1 
                
        if state == 'COOKED':
            if obj_name in obj["name"] and obj["isCooked"]:
                gcr_complete += 1 
                
        if state == 'OPENED':
            if obj_name in obj["name"] and obj["isOpen"]:
                gcr_complete += 1 
                
        if state == 'CLOSED':
            if obj_name in obj["name"] and not obj["isOpen"]:
                gcr_complete += 1 
                
        if state == 'PICKED':
            if obj_name in obj["name"] and obj["isPickedUp"]:
                gcr_complete += 1 
        
        if len(contains) != 0 and obj_name in obj["name"]:
            print (contains, obj_name, obj["name"])   
            for rec in contains:
                if obj['receptacleObjectIds'] is not None:
                    for r in obj['receptacleObjectIds']:
                        print (rec, r)
                        if rec in r:
                            print (rec, r)
                            gcr_complete += 1 
                    
            
             
sr = 0
tc = 0
if gcr_tasks == 0:
    gcr = 1
else:
    gcr = gcr_complete / gcr_tasks

if gcr == 1.0:
    tc = 1 
    
max_trans += 1
no_trans_gt += 1
print (no_trans_gt, max_trans, no_trans)
if max_trans == no_trans_gt and no_trans_gt == no_trans:
    ru = 1
elif max_trans == no_trans_gt:
    ru = 0
else:
    ru =  (max_trans - no_trans) / (max_trans - no_trans_gt)

if tc == 1 and ru == 1:
    sr = 1

print (f"SR:{sr}, TC:{tc}, GCR:{gcr}, Exec:{exec}, RU:{ru}")

# 비디오 라이터 정리
try:
    if 'video_writer' in globals() and video_writer is not None:
        video_writer.release()
        print("통합 비디오 저장 완료: 로그 폴더 내 combined_visualization.mp4")
except NameError:
    pass

# 기존 개별 비디오 생성 기능 제거 (이미지 저장을 하지 않으므로)
# generate_video()
