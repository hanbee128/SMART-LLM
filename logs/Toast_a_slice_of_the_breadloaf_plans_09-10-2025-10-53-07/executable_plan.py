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


ground_truth = [{'name': 'Bread', 'contains': [], 'state': 'COOKED'}]
no_trans_gt = 0
max_trans = 1

import numpy as np
import time
import sys
import os
import math
import re
import random
import cv2
import threading
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))
from astar_pathfinding import AStarPathfinding, plan_path_astar, find_optimal_robot_positions_astar

total_exec = 0
success_exec = 0

# 이미지 저장 기능 제거됨

def distance_pts(p1, p2):
    """두 점 사이의 거리를 계산하는 함수"""
    return ((p1[0] - p2[0]) ** 2 + (p1[2] - p2[2]) ** 2) ** 0.5

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
    global total_exec, success_exec
    
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
                    multi_agent_event = c.step(action="PutObject", objectId=act['objectId'], agentId=act['agent_id'], forceAction=True)
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
 
                
                elif act['action'] == 'DropHandObject':
                    total_exec += 1
                    multi_agent_event = c.step(action="DropHandObject", agentId=act['agent_id'], forceAction=True)
                    if multi_agent_event.metadata['errorMessage'] != "":
                        print(f"❌ DropHandObject 실패: {multi_agent_event.metadata['errorMessage']}")
                    else:
                        print(f"✅ DropHandObject 성공: 로봇 {act['agent_id']}이 손에 들고 있던 객체를 떨어뜨렸습니다.")
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
            
            if cv2.waitKey(25) & 0xFF == ord('q'):
                break
            
            img_counter += 1    
            action_queue.pop(0)
       
actions_thread = threading.Thread(target=exec_actions)
actions_thread.start()

def GoToObject(robots, dest_obj):
    """
    A* 알고리즘을 사용하여 로봇을 목표 객체로 이동시키는 함수 (aithor_connect 버전)
    
    Args:
        robots: 로봇 객체 또는 로봇 객체 리스트
        dest_obj: 목표 객체 이름
    """
    global recp_id
    
    print(f"🎯 A* 경로 계획으로 이동 중: {dest_obj}")
    
    # 로봇이 리스트가 아닌 경우 리스트로 변환
    if not isinstance(robots, list):
        robots = [robots]
    
    no_agents = len(robots)
    
    # 목표 객체의 위치 찾기
    objs = list([obj["objectId"] for obj in c.last_event.metadata["objects"]])
    objs_center = list([obj["axisAlignedBoundingBox"]["center"] for obj in c.last_event.metadata["objects"]])
    
    dest_obj_id = None
    dest_obj_center = None
    
    if "|" in dest_obj:
        # 객체 ID가 이미 주어진 경우 (위치 정보 포함)
        dest_obj_id = dest_obj
        pos_arr = dest_obj_id.split("|")
        dest_obj_center = {'x': float(pos_arr[1]), 'y': float(pos_arr[2]), 'z': float(pos_arr[3])}
    else:
        # 객체 이름으로 찾기
        min_distance = float('inf')
        
        # 여러 개의 같은 타입 객체가 있을 때 가장 가까운 것 선택
        for idx, obj in enumerate(objs):
            if dest_obj in obj:  # 부분 매칭 사용
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
            print(f"❌ 목표 객체를 찾을 수 없습니다: {dest_obj}")
            print(f"사용 가능한 객체들: {objs[:10]}...")  # 처음 10개만 표시
            return
    
    dest_obj_pos = (dest_obj_center['x'], dest_obj_center['y'], dest_obj_center['z'])
    print(f"📍 목표 객체 위치: {dest_obj_pos}")
    
    # A* 경로 계획 인스턴스 생성
    astar = AStarPathfinding(reachable_positions)
    
    # 각 로봇의 현재 위치와 목표 위치 수집
    robot_positions = []
    robot_goals = []
    
    for robot in robots:
        robot_name = robot['name']
        agent_id = int(robot_name[-1]) - 1
        
        # 로봇의 현재 위치
        metadata = c.last_event.events[agent_id].metadata
        current_pos = (
            metadata["agent"]["position"]["x"],
            metadata["agent"]["position"]["y"],
            metadata["agent"]["position"]["z"]
        )
        robot_positions.append(current_pos)
        robot_goals.append(dest_obj_pos)
    
    # 각 로봇에 대해 A* 경로 계획 실행
    robot_paths = []
    occupied_positions = set()
    
    for i, robot in enumerate(robots):
        print(f"🤖 로봇 {i+1} 경로 계획 중...")
        
        # 현재 로봇의 경로 계획
        path = astar.find_path(robot_positions[i], robot_goals[i])
        
        if not path:
            print(f"❌ 로봇 {i+1}의 경로를 찾을 수 없습니다.")
            continue
            
        robot_paths.append(path)
        
        # 경로의 중간 지점들을 점유 위치로 등록 (충돌 회피)
        for pos in path[1:-1]:  # 시작점과 끝점 제외
            occupied_positions.add(pos)
    
    # 경로를 따라 이동 실행
    goal_thresh = 0.25
    max_iterations = 100
    iteration = 0
    
    while iteration < max_iterations:
        all_reached = True
        
        for i, robot in enumerate(robots):
            if i >= len(robot_paths) or not robot_paths[i]:
                continue
                
            robot_name = robot['name']
            agent_id = int(robot_name[-1]) - 1
            
            # 로봇의 현재 위치
            metadata = c.last_event.events[agent_id].metadata
            current_pos = (
                metadata["agent"]["position"]["x"],
                metadata["agent"]["position"]["y"],
                metadata["agent"]["position"]["z"]
            )
            
            # 목표까지의 거리 계산
            dist_to_goal = distance_pts(current_pos, dest_obj_pos)
            
            if dist_to_goal > goal_thresh:
                all_reached = False
                
                # 다음 경로 지점으로 이동
                if robot_paths[i]:
                    next_waypoint = robot_paths[i][0]
                    action_queue.append({
                        'action': 'ObjectNavExpertAction',
                        'position': dict(x=next_waypoint[0], y=next_waypoint[1], z=next_waypoint[2]),
                        'agent_id': agent_id
                    })
                    
                    # 도달한 경로 지점 제거
                    if distance_pts(current_pos, next_waypoint) < 0.5:
                        robot_paths[i].pop(0)
            else:
                print(f"✅ 로봇 {i+1}이 목표에 도달했습니다!")
        
        if all_reached:
            break
            
        iteration += 1
        time.sleep(0.5)
    
    # 모든 로봇이 목표에 도달했는지 확인
    for i, robot in enumerate(robots):
        robot_name = robot['name']
        agent_id = int(robot_name[-1]) - 1
        
        metadata = c.last_event.events[agent_id].metadata
        current_pos = (
            metadata["agent"]["position"]["x"],
            metadata["agent"]["position"]["y"],
            metadata["agent"]["position"]["z"]
        )
        
        dist_to_goal = distance_pts(current_pos, dest_obj_pos)
        if dist_to_goal <= goal_thresh:
            print(f"✅ 로봇 {i+1}이 {dest_obj}에 성공적으로 도달했습니다!")
        else:
            print(f"⚠️ 로봇 {i+1}이 목표에 도달하지 못했습니다. 거리: {dist_to_goal:.2f}")
    
    # 목표 객체를 향해 회전
    for robot in robots:
        robot_name = robot['name']
        agent_id = int(robot_name[-1]) - 1
        
        metadata = c.last_event.events[agent_id].metadata
        robot_location = {
            "x": metadata["agent"]["position"]["x"],
            "y": metadata["agent"]["position"]["y"],
            "z": metadata["agent"]["position"]["z"],
            "rotation": metadata["agent"]["rotation"]["y"]
        }
        
        # 목표 객체를 향한 각도 계산
        robot_object_vec = [dest_obj_pos[0] - robot_location['x'], dest_obj_pos[2] - robot_location['z']]
        y_axis = [0, 1]
        unit_y = y_axis / np.linalg.norm(y_axis)
        unit_vector = robot_object_vec / np.linalg.norm(robot_object_vec)
        
        angle = math.atan2(np.linalg.det([unit_vector, unit_y]), np.dot(unit_vector, unit_y))
        angle = 360 * angle / (2 * np.pi)
        angle = (angle + 360) % 360
        rot_angle = angle - robot_location['rotation']
        
        if abs(rot_angle) > 5:  # 5도 이상 차이가 날 때만 회전
            if rot_angle > 0:
                action_queue.append({'action': 'RotateRight', 'degrees': abs(rot_angle), 'agent_id': agent_id})
            else:
                action_queue.append({'action': 'RotateLeft', 'degrees': abs(rot_angle), 'agent_id': agent_id})
    
    print(f"🎯 A* 경로 계획 완료: {dest_obj}")
    
    # 수신기 객체인 경우 전역 변수에 저장
    if dest_obj in ["Cabinet", "Fridge", "CounterTop", "Drawer", "Toaster", "Table", "Shelf"]:
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
            # 객체 이름 매칭 (문자열 어디에 있든 찾기)
            if pick_obj in obj:
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
    always_open_containers = ["CounterTop", "Table", "Shelf", "Floor", "Wall", "Bowl", "Plate", "Cup", "Mug", "Box", "GarbageCan", "Toaster"]
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
    action_queue.append({'action':'PutObject', 'objectId':recp_obj_id, 'agent_id':agent_id})
    time.sleep(1)
    
    # PutObject 실행 후 상태 확인
    time.sleep(2)  # 액션 완료 대기
    
    # 수신기 내부 객체 확인
    try:
        # 수신기 객체 찾기
        recp_objects = []
        for obj in c.last_event.metadata["objects"]:
            if re.match(recp, obj["objectId"]):
                if "receptacleObjectIds" in obj and obj["receptacleObjectIds"]:
                    recp_objects = obj["receptacleObjectIds"]
                    break
        
        # 배치 결과 확인
        if recp_objects:
            print(f"✅ 성공: 객체가 {recp}에 배치됨")
            print(f"수신기 내부 객체들: {recp_objects}")
            return True
        else:
            print(f"❌ 실패: 객체가 {recp}에 배치되지 않음")
            return False
            
    except Exception as e:
        print(f"상태 확인 중 오류: {e}")
        return False
         
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
    
    # 객체가 토글 가능한지 확인 (Toaster는 특별 처리)
    toggleable_objects = ["Toaster", "StoveBurner", "Lamp", "Television", "Computer", "Laptop", "Microwave"]
    is_known_toggleable = any(obj in toggle_obj for obj in toggleable_objects)
    
    if toggle_obj_metadata and not toggle_obj_metadata.get('toggleable', False) and not is_known_toggleable:
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

def ToggleObjectOff(robot, toggle_obj):
    """객체를 끄는 함수"""
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
    
    # 객체가 토글 가능한지 확인 (Toaster는 특별 처리)
    toggleable_objects = ["Toaster", "StoveBurner", "Lamp", "Television", "Computer", "Laptop", "Microwave"]
    is_known_toggleable = any(obj in toggle_obj for obj in toggleable_objects)
    
    if toggle_obj_metadata and not toggle_obj_metadata.get('toggleable', False) and not is_known_toggleable:
        print(f"❌ {toggle_obj}는 토글할 수 없는 객체입니다.")
        return
    
    # 이미 꺼져있는지 확인
    if toggle_obj_metadata and not toggle_obj_metadata.get('isToggled', True):
        print(f"ℹ️ {toggle_obj}는 이미 꺼져있습니다.")
        return
    
    GoToObject(robot, toggle_obj_id)
    time.sleep(1)
    print(f"Toggle Off: {toggle_obj}")
    action_queue.append({'action':'ToggleObjectOff', 'objectId':toggle_obj_id, 'agent_id':agent_id})
    time.sleep(1)
    
    # ToggleObjectOff 액션 실행
    multi_agent_event = c.step(action="ToggleObjectOff", objectId=toggle_obj_id, agentId=agent_id)
    if multi_agent_event.metadata['errorMessage'] != "":
        print(f"❌ 실패: {toggle_obj} 끄기 실패 - {multi_agent_event.metadata['errorMessage']}")
    else:
        print(f"✅ 성공: {toggle_obj}가 꺼졌습니다.")
    
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

def DropHandObject(robot):
    """로봇이 손에 들고 있는 객체를 떨어뜨리는 함수"""
    print("Dropping hand object...")
    robot_name = robot['name']
    agent_id = int(robot_name[-1]) - 1
    
    # 로봇이 손에 들고 있는 객체가 있는지 확인
    try:
        metadata = c.last_event.events[agent_id].metadata
        inventory_objects = metadata.get('inventoryObjects', [])
        
        if not inventory_objects:
            print(f"❌ 로봇 {agent_id + 1}이 손에 들고 있는 객체가 없습니다.")
            return False
        
        print(f"✅ 로봇 {agent_id + 1}이 손에 들고 있는 객체: {inventory_objects}")
        
        # DropHandObject 액션 실행
        action_queue.append({'action':'DropHandObject', 'agent_id':agent_id})
        time.sleep(1)
        
        print(f"✅ 로봇 {agent_id + 1}이 손에 들고 있던 객체를 떨어뜨렸습니다.")
        return True
        
    except Exception as e:
        print(f"❌ DropHandObject 실행 중 오류 발생: {e}")
        return False

def CheckToasterContents():
    """Toaster 내부 객체들을 확인하는 디버깅 함수"""
    print("🔍 Toaster 내부 객체 확인 중...")
    
    for obj in c.last_event.metadata["objects"]:
        if "Toaster" in obj["objectId"]:
            print(f"📦 Toaster 객체: {obj['objectId']}")
            print(f"🔧 Toaster 속성들:")
            print(f"  - openable: {obj.get('openable', 'N/A')}")
            print(f"  - pickupable: {obj.get('pickupable', 'N/A')}")
            print(f"  - toggleable: {obj.get('toggleable', 'N/A')}")
            print(f"  - isOpen: {obj.get('isOpen', 'N/A')}")
            print(f"  - receptacleObjectIds: {obj.get('receptacleObjectIds', 'N/A')}")
            
            if "receptacleObjectIds" in obj:
                receptacle_objects = obj["receptacleObjectIds"]
                if receptacle_objects:
                    print(f"✅ Toaster 내부 객체들: {receptacle_objects}")
                    # BreadSliced_1~6이 포함되어 있는지 확인
                    bread_sliced_objects = [obj_id for obj_id in receptacle_objects if "BreadSliced_" in obj_id]
                    if bread_sliced_objects:
                        print(f"🍞 발견된 빵 조각들: {bread_sliced_objects}")
                    else:
                        print("❌ Toaster에 빵 조각이 없습니다.")
                else:
                    print("❌ Toaster가 비어있습니다.")
            else:
                print("❌ Toaster에 receptacleObjectIds 속성이 없습니다.")
            break
    else:
        print("❌ Toaster 객체를 찾을 수 없습니다.")

def CheckBreadSlicedProperties():
    """BreadSliced 객체들의 속성을 확인하는 디버깅 함수"""
    print("🔍 BreadSliced 객체들 속성 확인 중...")
    
    for obj in c.last_event.metadata["objects"]:
        if "BreadSliced_" in obj["objectId"]:
            print(f"🍞 {obj['objectId']}:")
            print(f"  - pickupable: {obj.get('pickupable', 'N/A')}")
            print(f"  - visible: {obj.get('visible', 'N/A')}")
            print(f"  - position: {obj.get('position', 'N/A')}")
            print(f"  - parentReceptacles: {obj.get('parentReceptacles', 'N/A')}")
            print(f"  - receptacleObjectIds: {obj.get('receptacleObjectIds', 'N/A')}")
            print("---")
def toast_bread(robot_list):
    # robot_list = [robot1]
    # 0: Go to the Knife using robot1.
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
    # 6: Pick up the toasted Bread using robot1.
    PickupObject(robot_list[0], 'BreadSliced_1')

# Execute SubTask
toast_bread([robots[0]])

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
