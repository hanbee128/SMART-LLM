# IMPORTANT: Always use AI2Thor action functions (GoToObject, PickupObject, PutObject, etc.)
# and include function calls at the end to execute the task!

# EXAMPLE 1 - Task Description: Toast a slice of the breadloaf
# GENERAL TASK DECOMPOSITION
# Independent subtasks:
# SubTask 1: Toast a slice of the breadloaf. (Skills Required: GoToObject, PickupObject, PutObject, SwitchOn, SwitchOff)
# We can perform SubTask 1

# TASK ALLOCATION
robots = [{'name': 'robot1', 'skills': ['GoToObject', 'SwitchOn', 'SwitchOff'], 'mass': 100}, {'name': 'robot2', 'skills': ['GoToObject', 'PickupObject', 'PutObject'], 'mass': 100}, {'name': 'robot3', 'skills': ['GoToObject', 'SliceObject', 'PickupObject'], 'mass': 100}]
# SOLUTION
# All the robots DONOT share the same set and number of skills & all objects have different masses. In this case where all robots have different sets of skills and objects have different mass - Focus on Task Allocation based on Robot Skills alone. 
# Analyze the skills required for each subtask and the skills each robot possesses. In this scenario, we have one main subtask: 'Toast a slice of the breadloaf'.
# For the 'Toast a slice of the breadloaf' subtask, it requires 'GoToObject', 'PickupObject', 'PutObject', 'SwitchOn', and 'SwitchOff' skills. 
# Robot 2 has 'GoToObject', 'PickupObject', 'PutObject' skills for handling the bread.
# Robot 1 has 'GoToObject', 'SwitchOn', 'SwitchOff' skills for controlling the toaster.
# No teams are required since SubTasks can be performed with individual robots as explained above. The 'Toast a slice of the breadloaf' subtask is assigned to Robot 1 and Robot 2 working together. 

# Code Solution 
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
# Task toast a slice of the breadloaf is done

# EXAMPLE 2 - Task Description: Put the apple in the fridge
# GENERAL TASK DECOMPOSITION
# Independent subtasks:
# SubTask 1: Put the apple in the fridge. (Skills Required: GoToObject, PickupObject, PutObject)

# TASK ALLOCATION
robots = [{'name': 'robot1', 'skills': ['GoToObject', 'PickupObject', 'PutObject'], 'mass': 100}]
# SOLUTION
# For the 'Put the apple in the fridge' subtask, it requires 'GoToObject', 'PickupObject', and 'PutObject' skills.
# Robot 1 has all the required skills.

# Code Solution 
def put_apple_in_fridge(robot_list):
    # robot_list = [robot1]
    # 0: SubTask 1: Put the apple in the fridge
    # 1: Go to the Apple using robot1.
    GoToObject(robot_list[0], 'Apple')
    # 2: Pick up the Apple using robot1.
    PickupObject(robot_list[0], 'Apple')
    # 3: Go to the Fridge using robot1.
    GoToObject(robot_list[0], 'Fridge')
    # 4: Put the Apple in the Fridge using robot1.
    PutObject(robot_list[0], 'Apple', 'Fridge')

# Execute SubTask 1
put_apple_in_fridge([robots[0]])
# Task put the apple in the fridge is done


# EXAMPLE 2 - Task Description: Put tomato in fridge 
# GENERAL TASK DECOMPOSITION
# Independent subtasks:
# SubTask 1: Put Tomato in Fridge. (Skills Required: GoToObject, PickupObject, OpenObject, PutObject, CloseObject)
# We can perform SubTask 1.

# TASK ALLOCATION
robots = [{'name': 'robot1', 'skills': ['GoToObject', 'OpenObject', 'CloseObject', 'BreakObject', 'SliceObject', 'PickupObject', 'PutObject', 'SwitchOn', 'SwitchOff', 'DropHandObject', 'ThrowObject', 'PushObject', 'PullObject'],'mass': 4}, {'name': 'robot2', 'skills': ['GoToObject', 'OpenObject', 'CloseObject', 'BreakObject', 'SliceObject', 'PickupObject', 'PutObject', 'SwitchOn', 'SwitchOff', 'DropHandObject', 'ThrowObject', 'PushObject', 'PullObject'],'mass': 1}, {'name': 'robot3', 'skills': ['GoToObject', 'OpenObject', 'CloseObject', 'BreakObject', 'SliceObject', 'PickupObject', 'PutObject', 'SwitchOn', 'SwitchOff', 'DropHandObject', 'ThrowObject', 'PushObject', 'PullObject'],'mass': 2}]
# SOLUTION
# All the robots share the same set and number of skills (no_skills) & all objects DONOT have same mass. In this case where all objects have different mass, and robots have same sets of skills- Focus on Task Allocation based on Mass alone. 
# Analyze the mass required for each object being PickedUp by the 'PickupObject' skill, and the mass capacity each robot possesses. In this scenario, we have one main subtasks: 'Put Tomato in Fridge.'.
# For the 'Put Tomato in Fridge.' subtask, mass of the Tomato is 4. Hence the subtask can be performed by any robot with mass capacity greater than or equal to 4. In this case, Robots 1 has a mass capacity = 4.
# No teams are required since SubTasks can be performed with individual robots as explained above. The 'Put Tomato in Fridge.' subtask is assigned to Robot 1. 

# Code Solution 
def put_tomato_in_fridge(robot_list):
    # robot_list = [robot1]
    # 0: SubTask 1: Put Tomato in Fridge
    # 1: Go to the Tomato using robot1.
    GoToObject(robot_list[0], 'Tomato')
    # 2: Pick up the Tomato using robot1.
    PickupObject(robot_list[0], 'Tomato')
    # 3: Go to the Fridge using robot1.
    GoToObject(robot_list[0], 'Fridge')
    # 4: Open the Fridge using robot1.
    OpenObject(robot_list[0], 'Fridge')
    # 5: Put the Tomato in the Fridge using robot1.
    PutObject(robot_list[0], 'Tomato', 'Fridge')
    # 6: Close the Fridge using robot1.
    CloseObject(robot_list[0], 'Fridge')
# Perform SubTask 1 
put_tomato_in_fridge([robots[0]])

# Task Put tomato in fridge is done


# EXAMPLE 3 - Task Description: Slice the Potato 
# GENERAL TASK DECOMPOSITION
# Independent subtasks:
# SubTask 1: Slice the Potato. (Skills Required: GoToObject, PickupObject, SliceObject, PutObject)
# We can execute SubTask 1 first.

# TASK ALLOCATION
robots = [{'name': 'robot1', 'skills': ['GoToObject', 'OpenObject', 'CloseObject', 'BreakObject', 'SliceObject'],'mass': 2}, {'name': 'robot2', 'skills': ['GoToObject', 'OpenObject', 'CloseObject', 'BreakObject', 'SwitchOn', 'SwitchOff', 'DropHandObject', 'ThrowObject', 'PushObject', 'PullObject'],'mass': 2}, {'name': 'robot3', 'skills': ['GoToObject', 'OpenObject', 'CloseObject', 'BreakObject', 'PickupObject', 'PutObject', 'DropHandObject'],'mass': 2}]
# SOLUTION
# All the robots DONOT share the same set and number of skills (no_skills) & all objects have different masses. In this case where all robots have different sets of skills and objects have different mass - Focus on Task Allocation based on Robot Skills alone. 
# Analyze the skills required for each subtask and the skills each robot possesses. In this scenario, we have one main subtasks: 'Slice the Potato'.
# For the 'Slice the Potato' subtask, it can be performed by any robot with 'GoToObject', 'PickupObject', 'SliceObject' and 'PutObject' skills. However, no individual robot has all these skills. This is a skill gap that needs to be addressed. Form a team of robots. The skills of the team must be 'GoToObject', 'PickupObject', 'SliceObject' and 'PutObject' skills. Team of Robots 1 and 3 have all the skills required where robot 1 has the 'SliceObject' skill and Robot 3 has the 'GoToObject', 'PickupObject', and 'PutObject' skills.
# Teams are required since SubTasks can't be performed with individual robots as explained above. The 'Slice the Potato' subtask is assigned to team of Robots 1 and 3. 

# Code Solution
def slice_potato(robot_list):
    # robot_list = [robot1,robot3]
    # 0: SubTask 1: Slice the Potato
    # 1: Go to the Knife  using robot3.
    GoToObject(robot_list[1], 'Knife')
    # 2: Pick up the Knife using robot3.
    PickupObject(robot_list[1], 'Knife')
    # 3: Go to the Potato using robot3.
    GoToObject(robot_list[1], 'Potato')
    # 4: Slice the Potato using robot1.
    SliceObject(robot_list[0], 'Potato')
    # 5: Go to the countertop using robot3.
    GoToObject(robot_list[1], 'CounterTop')
    # 6: Put the Knife back on the CounterTop using robot3.
    PutObject(robot_list[1], 'Knife', 'CounterTop')
# Execute SubTask 1
slice_potato([robots[0], robots[2]])

# IMPORTANT: Always include function calls at the end to execute the task!
# Example patterns:
# function_name([robots[0], robots[1]])
# function_name([robots[0], robots[2]])
# function_name([robots[1], robots[2]])
# Task slice the potato is done


# EXAMPLE 4 - Task Description: Throw the fork in the trash
# GENERAL TASK DECOMPOSITION
# Independent subtasks:
# SubTask 1: Pick up the Fork. (Skills Required: GoToObject, PickupObject)
# SubTask 2: Throw the Fork in the Trash. (Skills Required: GoToObject, ThrowObject)
# We can execute SubTask 1 first and then SubTask 2.

# TASK ALLOCATION
robots = [{'name': 'robot1', 'skills': ['GoToObject', 'OpenObject', 'CloseObject', 'BreakObject', 'SliceObject', 'PickupObject', 'PutObject', 'SwitchOn', 'SwitchOff', 'DropHandObject', 'ThrowObject', 'PushObject', 'PullObject'],'mass': 3}, {'name': 'robot2', 'skills': ['GoToObject', 'OpenObject', 'CloseObject', 'BreakObject', 'SliceObject', 'PickupObject', 'PutObject', 'SwitchOn', 'SwitchOff', 'DropHandObject', 'ThrowObject', 'PushObject', 'PullObject'],'mass': 2}, {'name': 'robot3', 'skills': ['GoToObject', 'OpenObject', 'CloseObject', 'BreakObject', 'SliceObject', 'PickupObject', 'PutObject', 'SwitchOn', 'SwitchOff', 'DropHandObject', 'ThrowObject', 'PushObject', 'PullObject'],'mass': 2}]
# SOLUTION
# All the robots share the same set and number of skills (no_skills) & all objects DONOT have same mass. In this case where all objects have different mass, and robots have same sets of skills- Focus on Task Allocation based on Mass alone. 
# Analyze the mass required for each object being PickedUp by the 'PickupObject' skill, and the mass capacity each robot possesses. In this scenario, we have two main subtasks: 'Pick up the Fork' and 'Throw the Fork in the Trash'.
# For the 'Pick up the Fork' subtask, mass of the Fork is 5. Hence the subtask can be performed by any robot with mass capacity greater than or equal to 5. However, no individual robot has mass capacity of 5. This is a mass gap that needs to be addressed. Form a team of robots. The combined mass capacity of the team must be greater than or equal to 5. Team of Robots 1 and 2 have the mass capacity required where robot1 has mass capacity of 3 and where robot2 has mass capacity of 2 , this gives a combined mass capacity of 5.
# For the 'Throw the Fork in the Trash' subtask, mass of the Fork is 5. Hence the subtask can be performed by any robot with mass capacity greater than or equal to 5. However, no individual robot has mass capacity of 5. This is a mass gap that needs to be addressed. Form a team of robots. The combined mass capacity of the team must be greater than or equal to 5. Team of Robots 1 and 3 have the mass capacity required where robot1 has mass capacity of 3 and where robot3 has mass capacity of 2 , this gives a combined mass capacity of 5.
# Teams are required since SubTasks can't be performed with individual robots as explained above. The 'Pick up the Fork' subtask is assigned to team of Robots 1 and 2. The 'Throw the Fork in the Trash' subtask is assigned to team of Robots 1 and 3. 

# CODE Solution
def pick_up_fork(robot_list):
    # robot_list = [robot1,robot2]
    # 0: SubTask 1: Pick up the Fork
    # 1: Go to the Fork using robot1.
    GoToObject(robot_list[0], 'Fork')
    # 2: Pick up the Fork using robot1.
    PickupObject(robot_list[0], 'Fork')

def throw_fork_in_trash(robot_list):
    # robot_list = [robot1,robot3]
    # 0: SubTask 2: Throw the Fork in the Trash
    # 1: Go to the GarbageCan using robot1.
    GoToObject(robot_list[0], 'GarbageCan')
    # 2: Throw the Fork in the GarbageCan using robot1.
    ThrowObject(robot_list[0], 'Fork', 'GarbageCan')

# Execute SubTask 1
pick_up_fork([robots[0], robots[1]])

# Execute SubTask 2
throw_fork_in_trash([robots[0], robots[2]])

# Task throw the fork in the trash is done