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
from astar_pathfinding import AStarPathfinding, plan_path_astar, find_optimal_robot_positions_astar

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

def generate_video(input_path, prefix, char_id=0, image_synthesis=['normal'], frame_rate=5, output_path=None):
    """ Generate a video of an episode """
    if output_path is None:
        output_path = input_path

    vid_folder = '{}/{}/{}/'.format(input_path, prefix, char_id)
    if not os.path.isdir(vid_folder):
        print("The input path: {} you specified does not exist.".format(input_path))
        return
    
    # ffmpeg가 설치되어 있는지 확인
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Warning: ffmpeg is not installed or not available. Skipping video generation.")
        return
    
    for vid_mod in image_synthesis:
        try:
            command_set = ['ffmpeg', '-i',
                             '{}/Action_%04d_0_{}.png'.format(vid_folder, vid_mod), 
                             '-framerate', str(frame_rate),
                             '-pix_fmt', 'yuv420p',
                             '{}/video_{}.mp4'.format(output_path, vid_mod)]
            result = subprocess.run(command_set, capture_output=True, text=True)
            if result.returncode == 0:
                print("Video generated at ", '{}/video_{}.mp4'.format(output_path, vid_mod))
            else:
                print(f"Warning: Failed to generate video for {vid_mod}. Error: {result.stderr}")
        except Exception as e:
            print(f"Error generating video for {vid_mod}: {str(e)}")

robots = [{'name': 'robot1', 'skills': ['GoToObject', 'OpenObject', 'CloseObject', 'BreakObject', 'SliceObject', 'SwitchOn', 'SwitchOff', 'PickupObject', 'PutObject', 'DropHandObject', 'ThrowObject', 'PushObject', 'PullObject']}, 
          {'name': 'robot2', 'skills': ['GoToObject', 'OpenObject', 'CloseObject', 'BreakObject', 'SliceObject', 'SwitchOn', 'SwitchOff', 'PickupObject', 'PutObject', 'DropHandObject', 'ThrowObject', 'PushObject', 'PullObject']}]

floor_no = 1

c = Controller( height=1000, width=1000)
c.reset("FloorPlan" + str(floor_no)) 
no_robot = len(robots)

# initialize n agents into the scene
multi_agent_event = c.step(dict(action='Initialize', agentMode="default", snapGrid=False, gridSize=0.25, rotateStepDegrees=20, visibilityDistance=100, fieldOfView=90, agentCount=no_robot))

# add a top view camera
event = c.step(action="GetMapViewCameraProperties")
event = c.step(action="AddThirdPartyCamera", **event.metadata["actionReturn"])

# get reachabel positions
reachable_positions_ = c.step(action="GetReachablePositions").metadata["actionReturn"]
reachable_positions = positions_tuple = [(p["x"], p["y"], p["z"]) for p in reachable_positions_]

# randomize postions of the agents
for i in range (no_robot):
    init_pos = random.choice(reachable_positions_)
    c.step(dict(action="Teleport", position=init_pos, agentId=i))

action_queue = []

task_over = False

def exec_actions():
    # 이미지 저장 기능 제거됨
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
                    multi_agent_event = c.step(action="PickupObject", objectId=act['objectId'], agentId=act['agent_id'], forceAction=True) 

                elif act['action'] == 'PutObject':
                    multi_agent_event = c.step(action="PutObject", objectId=act['objectId'], agentId=act['agent_id'], forceAction=True)
    
                elif act['action'] == 'ToggleObjectOn':
                    multi_agent_event = c.step(action="ToggleObjectOn", objectId=act['objectId'], agentId=act['agent_id'], forceAction=True)
                
                elif act['action'] == 'ToggleObjectOff':
                    multi_agent_event = c.step(action="ToggleObjectOff", objectId=act['objectId'], agentId=act['agent_id'], forceAction=True)
                
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
                
            for i,e in enumerate(multi_agent_event.events):
                cv2.imshow('agent%s' % i, e.cv2img)
            top_view_rgb = cv2.cvtColor(c.last_event.events[0].third_party_camera_frames[-1], cv2.COLOR_BGR2RGB)
            cv2.imshow('Top View', top_view_rgb)
            if cv2.waitKey(25) & 0xFF == ord('q'):
                break
            
            img_counter += 1    
            action_queue.pop(0)
            
actions_thread = threading.Thread(target=exec_actions)
actions_thread.start()

def GoToObject(robots, dest_obj):
    """
    A* 알고리즘을 사용하여 로봇을 목표 객체로 이동시키는 함수
    
    Args:
        robots: 로봇 객체 또는 로봇 객체 리스트
        dest_obj: 목표 객체 이름
    """
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
    
    # 목표 객체 찾기 (정확한 매칭)
    for idx, obj in enumerate(objs):
        if dest_obj in obj:  # 부분 매칭 사용
            dest_obj_id = obj
            dest_obj_center = objs_center[idx]
            break
    
    if dest_obj_id is None:
        print(f"❌ 목표 객체를 찾을 수 없습니다: {dest_obj}")
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
    goal_thresh = 0.3
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
    
def PickupObject(robot, pick_obj):
    robot_name = robot['name']
    agent_id = int(robot_name[-1]) - 1
    objs = list(set([obj["objectId"] for obj in c.last_event.metadata["objects"]]))
    
    for obj in objs:
        match = re.match(pick_obj, obj)
        if match is not None:
            pick_obj_id = obj
            break # find the first instance
        
    action_queue.append({'action':'PickupObject', 'objectId':pick_obj_id, 'agent_id':agent_id})
    
def PutObject(robot, put_obj, recp):
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
            dist = objs_dists[idx]# distance_pts(robot_location, [objs_center[idx]['x'], objs_center[idx]['y'], objs_center[idx]['z']])
            if dist < dist_to_recp:
                recp_obj_id = obj
                dest_obj_center = objs_center[idx]
                dist_to_recp = dist
    action_queue.append({'action':'PutObject', 'objectId':recp_obj_id, 'agent_id':agent_id})
         
def SwitchOn(robot, sw_obj):
    robot_name = robot['name']
    agent_id = int(robot_name[-1]) - 1
    objs = list(set([obj["objectId"] for obj in c.last_event.metadata["objects"]]))
    
    for obj in objs:
        match = re.match(sw_obj, obj)
        if match is not None:
            sw_obj_id = obj
            break # find the first instance
    
    action_queue.append({'action':'ToggleObjectOn', 'objectId':sw_obj_id, 'agent_id':agent_id})      
        
def SwitchOff(robot, sw_obj):
    robot_name = robot['name']
    agent_id = int(robot_name[-1]) - 1
    objs = list(set([obj["objectId"] for obj in c.last_event.metadata["objects"]]))
    
    for obj in objs:
        match = re.match(sw_obj, obj)
        if match is not None:
            sw_obj_id = obj
            break # find the first instance
    
    action_queue.append({'action':'ToggleObjectOff', 'objectId':sw_obj_id, 'agent_id':agent_id})        

def OpenObject(robot, sw_obj):
    robot_name = robot['name']
    agent_id = int(robot_name[-1]) - 1
    objs = list(set([obj["objectId"] for obj in c.last_event.metadata["objects"]]))
    
    for obj in objs:
        match = re.match(sw_obj, obj)
        if match is not None:
            sw_obj_id = obj
            break # find the first instance
    
    action_queue.append({'action':'OpenObject', 'objectId':sw_obj_id, 'agent_id':agent_id})
    
def CloseObject(robot, sw_obj):
    robot_name = robot['name']
    agent_id = int(robot_name[-1]) - 1
    objs = list(set([obj["objectId"] for obj in c.last_event.metadata["objects"]]))
    
    for obj in objs:
        match = re.match(sw_obj, obj)
        if match is not None:
            sw_obj_id = obj
            break # find the first instance
    
    action_queue.append({'action':'CloseObject', 'objectId':sw_obj_id, 'agent_id':agent_id}) 
    
def BreakObject(robot, sw_obj):
    robot_name = robot['name']
    agent_id = int(robot_name[-1]) - 1
    objs = list(set([obj["objectId"] for obj in c.last_event.metadata["objects"]]))
    
    for obj in objs:
        match = re.match(sw_obj, obj)
        if match is not None:
            sw_obj_id = obj
            break # find the first instance
    
    action_queue.append({'action':'BreakObject', 'objectId':sw_obj_id, 'agent_id':agent_id}) 
    
def SliceObject(robot, sw_obj):
    robot_name = robot['name']
    agent_id = int(robot_name[-1]) - 1
    objs = list(set([obj["objectId"] for obj in c.last_event.metadata["objects"]]))
    
    for obj in objs:
        match = re.match(sw_obj, obj)
        if match is not None:
            sw_obj_id = obj
            break # find the first instance
    
    action_queue.append({'action':'SliceObject', 'objectId':sw_obj_id, 'agent_id':agent_id})      
  
def CleanObject(robot, sw_obj):
    robot_name = robot['name']
    agent_id = int(robot_name[-1]) - 1
    objs = list(set([obj["objectId"] for obj in c.last_event.metadata["objects"]]))

    for obj in objs:
        match = re.match(sw_obj, obj)
        if match is not None:
            sw_obj_id = obj
            break # find the first instance

    action_queue.append({'action':'CleanObject', 'objectId':sw_obj_id, 'agent_id':agent_id}) 
 
# LLM Generated Code
 
def wash_apple(robot):
    # 0: Task 1: Wash the Apple
    # 1: Go to the Apple.
    GoToObject(robot, 'Apple')
    # 2: Pick up the Apple.
    PickupObject(robot, 'Apple')
    # 3: Go to the Sink.
    GoToObject(robot, 'Sink')
    # 4: Put the Apple in the Sink.
    PutObject(robot, 'Apple', 'Sink')
    # 5: Switch on the Faucet.
    SwitchOn(robot, 'Faucet')
    # 6: Wait for a while to let the Apple wash.
    time.sleep(5)
    # 7: Switch off the Faucet.
    SwitchOff(robot, 'Faucet')
    # 8: Pick up the washed Apple.
    PickupObject(robot, 'Apple')
    # 9: Go to the CounterTop.
    GoToObject(robot, 'CounterTop')
    # 10: Put the washed Apple on the CounterTop.
    PutObject(robot, 'Apple', 'CounterTop')

def wash_tomato(robot):
    # 0: Task 2: Wash the Tomato
    # 1: Go to the Tomato.
    GoToObject(robot, 'Tomato')
    # 2: Pick up the Tomato.
    PickupObject(robot, 'Tomato')
    # 3: Go to the Sink.
    GoToObject(robot, 'Sink')
    # 4: Put the Tomato in the Sink.
    PutObject(robot, 'Tomato', 'Sink')
    # 5: Switch on the Faucet.
    SwitchOn(robot, 'Faucet')
    # 6: Wait for a while to let the Tomato wash.
    time.sleep(5)
    # 7: Switch off the Faucet.
    SwitchOff(robot, 'Faucet')
    # 8: Pick up the washed Tomato.
    PickupObject(robot, 'Tomato')
    # 9: Go to the CounterTop.
    GoToObject(robot, 'CounterTop')
    # 10: Put the washed Tomato on the CounterTop.
    PutObject(robot, 'Tomato', 'CounterTop')

def wash_lettuce(robot):
    # 0: Task 3: Wash the Lettuce
    # 1: Go to the Lettuce.
    GoToObject(robot, 'Lettuce')
    # 2: Pick up the Lettuce.
    PickupObject(robot, 'Lettuce')
    # 3: Go to the Sink.
    GoToObject(robot, 'Sink')
    # 4: Put the Lettuce in the Sink.
    PutObject(robot, 'Lettuce', 'Sink')
    # 5: Switch on the Faucet.
    SwitchOn(robot, 'Faucet')
    # 6: Wait for a while to let the Lettuce wash.
    time.sleep(5)
    # 7: Switch off the Faucet.
    SwitchOff(robot, 'Faucet')
    # 8: Pick up the washed Lettuce.
    PickupObject(robot, 'Lettuce')
    # 9: Go to the CounterTop.
    GoToObject(robot, 'CounterTop')
    # 10: Put the washed Lettuce on the CounterTop.
    PutObject(robot, 'Lettuce', 'CounterTop')

def wash_potato(robot):
    # 0: Task 4: Wash the Potato
    # 1: Go to the Potato.
    GoToObject(robot, 'Potato')
    # 2: Pick up the Potato.
    PickupObject(robot, 'Potato')
    # 3: Go to the Sink.
    GoToObject(robot, 'Sink')
    # 4: Put the Potato in the Sink.
    PutObject(robot, 'Potato', 'Sink')
    # 5: Switch on the Faucet.
    SwitchOn(robot, 'Faucet')
    # 6: Wait for a while to let the Potato wash.
    time.sleep(5)
    # 7: Switch off the Faucet.
    SwitchOff(robot, 'Faucet')
    # 8: Pick up the washed Potato.
    PickupObject(robot, 'Potato')
    # 9: Go to the CounterTop.
    GoToObject(robot, 'CounterTop')
    # 10: Put the washed Potato on the CounterTop.
    PutObject(robot, 'Potato', 'CounterTop')
    
# Assign tasks to robots based on their skills
# Parallelize all tasks
# Assign Task1 to robot1 since it has all the skills to perform actions in Task 1
task1_thread = threading.Thread(target=wash_apple, args=(robots[0],))
# Assign Task2 to robot2 since it has all the skills to perform actions in Task 2
task2_thread = threading.Thread(target=wash_tomato, args=(robots[1],))

# Start executing Task 1 and Task 2 in parallel
task1_thread.start()
task2_thread.start()

# Wait for both Task 1 and Task 2 to finish
# actions_thread.join()
task1_thread.join()
task2_thread.join()

# Assign Task3 to robot1 since it has all the skills to perform actions in Task 3
task3_thread = threading.Thread(target=wash_lettuce, args=(robots[0],))
# Assign Task4 to robot2 since it has all the skills to perform actions in Task 4
task4_thread = threading.Thread(target=wash_potato, args=(robots[1],))

# Start executing Task 3 and Task 4 in parallel
task3_thread.start()
task4_thread.start()

# Wait for both Task 3 and Task 4 to finish
task3_thread.join()
task4_thread.join()

# Task wash_apple, wash_tomato, wash_lettuce, wash_potato is done
action_queue.append({'action':'Done'})
action_queue.append({'action':'Done'})
action_queue.append({'action':'Done'})

task_over = True
time.sleep(5)

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