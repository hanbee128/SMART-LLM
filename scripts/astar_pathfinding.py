"""
A* 경로 계획 알고리즘 구현
AI2THOR 환경에서 다중 로봇을 위한 A* 기반 경로 계획
"""

import numpy as np
import heapq
from typing import List, Tuple, Dict, Set
from dataclasses import dataclass
import math

@dataclass
class Node:
    """A* 알고리즘에서 사용하는 노드 클래스"""
    x: float
    y: float
    z: float
    g_cost: float = float('inf')  # 시작점에서의 실제 비용
    h_cost: float = 0.0           # 휴리스틱 비용 (목표점까지의 추정 비용)
    f_cost: float = float('inf')  # 총 비용 (g + h)
    parent: 'Node' = None
    
    def __lt__(self, other):
        return self.f_cost < other.f_cost
    
    def __eq__(self, other):
        return abs(self.x - other.x) < 0.1 and abs(self.y - other.y) < 0.1 and abs(self.z - other.z) < 0.1
    
    def __hash__(self):
        return hash((round(self.x, 1), round(self.y, 1), round(self.z, 1)))

class AStarPathfinding:
    """A* 경로 계획 클래스"""
    
    def __init__(self, reachable_positions: List[Tuple[float, float, float]], 
                 collision_radius: float = 0.5):
        """
        Args:
            reachable_positions: AI2THOR에서 제공하는 도달 가능한 위치들
            collision_radius: 로봇 간 충돌 회피를 위한 반경
        """
        self.reachable_positions = reachable_positions
        self.collision_radius = collision_radius
        self.occupied_positions: Set[Tuple[float, float, float]] = set()
        
    def euclidean_distance(self, pos1: Tuple[float, float, float], 
                          pos2: Tuple[float, float, float]) -> float:
        """유클리드 거리 계산"""
        return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2 + (pos1[2] - pos2[2])**2)
    
    def get_neighbors(self, node: Node) -> List[Node]:
        """현재 노드의 이웃 노드들을 반환"""
        neighbors = []
        
        for pos in self.reachable_positions:
            # 충돌 회피: 다른 로봇이 점유한 위치는 제외
            if pos in self.occupied_positions:
                continue
                
            # 너무 가까운 위치는 제외 (로봇 크기 고려)
            if self.euclidean_distance((node.x, node.y, node.z), pos) < self.collision_radius:
                continue
                
            neighbor = Node(pos[0], pos[1], pos[2])
            neighbors.append(neighbor)
            
        return neighbors
    
    def find_path(self, start: Tuple[float, float, float], 
                  goal: Tuple[float, float, float]) -> List[Tuple[float, float, float]]:
        """
        A* 알고리즘을 사용하여 시작점에서 목표점까지의 경로를 찾음
        
        Args:
            start: 시작 위치 (x, y, z)
            goal: 목표 위치 (x, y, z)
            
        Returns:
            경로를 나타내는 위치들의 리스트 (시작점 포함)
        """
        # 시작점과 목표점을 가장 가까운 도달 가능한 위치로 매핑
        start_node = self._find_closest_reachable_position(start)
        goal_node = self._find_closest_reachable_position(goal)
        
        if start_node is None or goal_node is None:
            print("❌ 시작점 또는 목표점에 도달 가능한 위치를 찾을 수 없습니다.")
            return []
        
        # A* 알고리즘 실행
        open_set = []
        closed_set = set()
        
        start_node.g_cost = 0
        start_node.h_cost = self.euclidean_distance((start_node.x, start_node.y, start_node.z), 
                                                   (goal_node.x, goal_node.y, goal_node.z))
        start_node.f_cost = start_node.g_cost + start_node.h_cost
        
        heapq.heappush(open_set, start_node)
        
        while open_set:
            current_node = heapq.heappop(open_set)
            
            # 목표점에 도달했는지 확인
            if self.euclidean_distance((current_node.x, current_node.y, current_node.z),
                                     (goal_node.x, goal_node.y, goal_node.z)) < 0.5:
                return self._reconstruct_path(current_node)
            
            closed_set.add(current_node)
            
            # 이웃 노드들 탐색
            for neighbor in self.get_neighbors(current_node):
                if neighbor in closed_set:
                    continue
                
                # 새로운 g_cost 계산
                tentative_g_cost = current_node.g_cost + self.euclidean_distance(
                    (current_node.x, current_node.y, current_node.z),
                    (neighbor.x, neighbor.y, neighbor.z)
                )
                
                # 더 좋은 경로를 찾았는지 확인
                if tentative_g_cost < neighbor.g_cost:
                    neighbor.parent = current_node
                    neighbor.g_cost = tentative_g_cost
                    neighbor.h_cost = self.euclidean_distance(
                        (neighbor.x, neighbor.y, neighbor.z),
                        (goal_node.x, goal_node.y, goal_node.z)
                    )
                    neighbor.f_cost = neighbor.g_cost + neighbor.h_cost
                    
                    # open_set에 추가 (중복 제거)
                    if neighbor not in open_set:
                        heapq.heappush(open_set, neighbor)
        
        print("❌ 경로를 찾을 수 없습니다.")
        return []
    
    def _find_closest_reachable_position(self, position: Tuple[float, float, float]) -> Node:
        """주어진 위치에서 가장 가까운 도달 가능한 위치를 찾음"""
        if not self.reachable_positions:
            return None
            
        min_distance = float('inf')
        closest_pos = None
        
        for pos in self.reachable_positions:
            distance = self.euclidean_distance(position, pos)
            if distance < min_distance:
                min_distance = distance
                closest_pos = pos
        
        if closest_pos:
            return Node(closest_pos[0], closest_pos[1], closest_pos[2])
        return None
    
    def _reconstruct_path(self, goal_node: Node) -> List[Tuple[float, float, float]]:
        """목표 노드에서 시작 노드까지의 경로를 재구성"""
        path = []
        current = goal_node
        
        while current is not None:
            path.append((current.x, current.y, current.z))
            current = current.parent
        
        path.reverse()
        return path
    
    def reserve_position(self, position: Tuple[float, float, float]):
        """특정 위치를 예약하여 다른 로봇이 사용하지 못하도록 함"""
        self.occupied_positions.add(position)
    
    def release_position(self, position: Tuple[float, float, float]):
        """예약된 위치를 해제"""
        self.occupied_positions.discard(position)
    
    def clear_reservations(self):
        """모든 예약을 해제"""
        self.occupied_positions.clear()

def find_optimal_robot_positions_astar(num_robots: int, 
                                     reachable_positions: List[Tuple[float, float, float]],
                                     start_positions: List[Tuple[float, float, float]]) -> List[Tuple[float, float, float]]:
    """
    A* 알고리즘을 사용하여 다중 로봇의 최적 위치를 찾음
    
    Args:
        num_robots: 로봇 수
        reachable_positions: 도달 가능한 위치들
        start_positions: 각 로봇의 시작 위치
        
    Returns:
        각 로봇의 최적 위치들
    """
    if num_robots == 0 or not reachable_positions:
        return []
    
    # A* 경로 계획 인스턴스 생성
    astar = AStarPathfinding(reachable_positions)
    
    # 각 로봇의 최적 위치 찾기
    optimal_positions = []
    
    for i in range(num_robots):
        if i < len(start_positions):
            # 시작 위치에서 가장 가까운 도달 가능한 위치 찾기
            closest_pos = astar._find_closest_reachable_position(start_positions[i])
            if closest_pos:
                optimal_positions.append((closest_pos.x, closest_pos.y, closest_pos.z))
                # 해당 위치를 예약하여 다른 로봇이 사용하지 못하도록 함
                astar.reserve_position((closest_pos.x, closest_pos.y, closest_pos.z))
            else:
                # 시작 위치가 도달 불가능한 경우, 사용 가능한 위치 중 하나 선택
                if reachable_positions:
                    pos = reachable_positions[i % len(reachable_positions)]
                    optimal_positions.append(pos)
                    astar.reserve_position(pos)
        else:
            # 시작 위치가 없는 경우, 사용 가능한 위치 중 하나 선택
            if reachable_positions:
                pos = reachable_positions[i % len(reachable_positions)]
                optimal_positions.append(pos)
                astar.reserve_position(pos)
    
    return optimal_positions

def plan_path_astar(start: Tuple[float, float, float], 
                   goal: Tuple[float, float, float],
                   reachable_positions: List[Tuple[float, float, float]],
                   occupied_positions: Set[Tuple[float, float, float]] = None) -> List[Tuple[float, float, float]]:
    """
    A* 알고리즘을 사용하여 경로를 계획
    
    Args:
        start: 시작 위치
        goal: 목표 위치
        reachable_positions: 도달 가능한 위치들
        occupied_positions: 다른 로봇이 점유한 위치들
        
    Returns:
        경로를 나타내는 위치들의 리스트
    """
    astar = AStarPathfinding(reachable_positions)
    
    if occupied_positions:
        astar.occupied_positions = occupied_positions.copy()
    
    return astar.find_path(start, goal)
