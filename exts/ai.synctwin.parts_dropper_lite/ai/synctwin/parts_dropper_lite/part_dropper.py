from pxr import Usd, UsdGeom, Gf, UsdLux, UsdGeom, Sdf, Tf, UsdPhysics, PhysxSchema
from omni.physx.scripts.physicsUtils import add_ground_plane
from omni.physx.scripts.utils import set_physics_scene_asyncsimrender


class PartDropper:
    def __init__(self) -> None:
        self._cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ['default', 'render'])

    def stage_bounds(self, stage) -> Gf.Range3d:
        bounds = self._cache.ComputeWorldBound(stage.GetPrimAtPath("/"))
        return bounds.GetRange()

    def set_container_usd(self, usd_path):
        self.container_stage = Usd.Stage.Open(usd_path)
        self.container_size = self.stage_bounds(self.container_stage).GetSize()
        
    def set_part_usd(self, usd_path):
        self.part_stage = Usd.Stage.Open(usd_path)
        self.part_size = self.stage_bounds(self.part_stage).GetSize()
    
    def create_ground_plane(self, stage):
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
        # light
        defaultPrimPath = "/World"
        sphereLight = UsdLux.SphereLight.Define(stage, defaultPrimPath + "/SphereLight")
        sphereLight.CreateRadiusAttr(150)
        sphereLight.CreateIntensityAttr(30000)
        sphereLight.AddTranslateOp().Set(Gf.Vec3f(650.0, 0.0, 1150.0))

        # Physics scene
        scene = UsdPhysics.Scene.Define(stage, defaultPrimPath + "/physicsScene")
        scene.CreateGravityDirectionAttr().Set(Gf.Vec3f(0.0, 0.0, -1.0))
        scene.CreateGravityMagnitudeAttr().Set(981.0)
        set_physics_scene_asyncsimrender(scene.GetPrim())

        # custom GPU buffers
        physxSceneAPI = PhysxSchema.PhysxSceneAPI.Apply(stage.GetPrimAtPath(defaultPrimPath + "/physicsScene"))
        physxSceneAPI.CreateGpuTempBufferCapacityAttr(16 * 1024 * 1024 * 2)        
        physxSceneAPI.CreateGpuHeapCapacityAttr(64 * 1024 * 1024 * 2)
        physxSceneAPI.CreateGpuFoundLostPairsCapacityAttr(256 * 1024 * 2)
        physxSceneAPI.CreateGpuMaxRigidPatchCountAttr(1000000)

        add_ground_plane(stage, "/World/GroundPlane", "Z", 750.0, Gf.Vec3f(0.0, 0.0, 0), Gf.Vec3f(0.5))