
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

# randomize postions of the agents
for i in range (no_robot):
    init_pos = random.choice(reachable_positions_)
    c.step(dict(action="Teleport", position=init_pos, agentId=i))
    
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
    
    # 1.5미터 거리로 이동
    avoidance_distance = 1.5
    
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
    
    # 막고 있는 로봇을 회피 위치로 이동 (ObjectNavExpertAction 사용)
    action_queue.append({
        'action': 'ObjectNavExpertAction',
        'position': dict(x=avoidance_position[0], y=avoidance_position[1], z=avoidance_position[2]),
        'agent_id': blocking_robot_id
    })
    
    # 잠시 대기
    time.sleep(1.0)

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
                # 즉시 충돌 감지 및 회피
                target_position = (crp[ia][0], crp[ia][1], crp[ia][2])
                blocking_robot = detect_immediate_collision(agent_id, target_position)
                
                if blocking_robot is not None:
                    # 바로 앞에서 막고 있는 로봇이 있음
                    print(f"⚠️ 로봇 {agent_id}의 바로 앞에 로봇 {blocking_robot}이 막고 있습니다.")
                    
                    # 회피 시도 횟수 체크
                    if blocking_robot not in avoidance_attempts:
                        avoidance_attempts[blocking_robot] = 0
                    
                    if avoidance_attempts[blocking_robot] < max_avoidance_attempts:
                        # 회피 위치 계산
                        avoidance_pos = find_avoidance_position(blocking_robot, agent_id, target_position)
                        if avoidance_pos is not None:
                            # 막고 있는 로봇을 회피 위치로 이동
                            execute_collision_avoidance(blocking_robot, avoidance_pos)
                            avoidance_attempts[blocking_robot] += 1
                            time.sleep(2.0)  # 회피 완료까지 대기
                        else:
                            print(f"❌ 로봇 {blocking_robot}의 회피 위치를 찾을 수 없습니다.")
                    else:
                        print(f"⚠️ 로봇 {blocking_robot}의 최대 회피 시도 횟수에 도달했습니다. 다른 전략을 사용합니다.")
                        # 대안: 현재 로봇이 다른 경로로 우회
                        clost_node_location[ia] += 1
                        count_since_update[ia] = 0
                        crp = closest_node(dest_obj_pos, reachable_positions, no_agents, clost_node_location)
                
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
        
        for idx, obj in enumerate(objs):
            match = re.match(pick_obj, obj)
            if match is not None:
                pick_obj_id = obj
                dest_obj_center = objs_center[idx]
                if dest_obj_center != {'x': 0.0, 'y': 0.0, 'z': 0.0}:
                    break # find the first instance
        # GoToObject(robot, pick_obj_id)
        # time.sleep(1)
        print ("Picking Up ", pick_obj_id, dest_obj_center)
        action_queue.append({'action':'PickupObject', 'objectId':pick_obj_id, 'agent_id':agent_id})
        time.sleep(1)
    
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
    
    # 수신기가 열려있는지 확인
    recp_is_open = False
    for obj in c.last_event.metadata["objects"]:
        if re.match(recp, obj["objectId"]):
            if "isOpen" in obj and obj["isOpen"]:
                recp_is_open = True
                break
    
    if not recp_is_open:
        print(f"❌ 실패: {recp}가 닫혀있어서 {put_obj}를 배치할 수 없습니다.")
        return False
    
    # PutObject 액션 실행
    print(f"PutObject 시도: {put_obj} -> {recp}")
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
        
        # 배치하려던 객체가 수신기 내부에 있는지 확인
        object_placed = False
        for recp_obj in recp_objects:
            if re.match(put_obj, recp_obj):
                object_placed = True
                break
        
        if object_placed:
            print(f"✅ 성공: {put_obj}가 {recp}에 배치됨")
            return True
        else:
            print(f"❌ 실패: {put_obj}가 {recp}에 배치되지 않음")
            print(f"수신기 내부 객체들: {recp_objects}")
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
    
def SliceObject(robot, sw_obj):
    print ("Slicing: ", sw_obj)
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