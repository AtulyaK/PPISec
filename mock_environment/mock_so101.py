import asyncio
from typing import List

class MockSO101:
    """
    Simulates the Viam SDK Arm component for local testing.
    Mimics joint movements and state reporting.
    """
    def __init__(self, name: str = "so101"):
        self.name = name
        self.joints = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.is_moving = False

    async def get_end_effector_pose(self):
        # Return a mock XYZ based on current joints
        return {"x": 10.0, "y": 20.0, "z": 5.0}

    async def move_to_joint_positions(self, positions: List[float]):
        print(f"[MockSO101] Moving to joints: {positions}")
        self.is_moving = True
        await asyncio.sleep(0.5) # Simulate travel time
        self.joints = positions
        self.is_moving = False
        print("[MockSO101] Move complete.")

    async def stop(self):
        self.is_moving = False
        print("[MockSO101] Emergency Stop.")

if __name__ == "__main__":
    arm = MockSO101()
    asyncio.run(arm.move_to_joint_positions([0, 45, 90, 0, 0, 0]))
