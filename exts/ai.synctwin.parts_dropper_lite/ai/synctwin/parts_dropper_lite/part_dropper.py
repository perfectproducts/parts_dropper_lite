from pxr import Usd, UsdGeom, Gf, UsdLux, UsdGeom, Sdf, Tf, UsdPhysics, PhysxSchema
from omni.physx.scripts.physicsUtils import add_ground_plane
from omni.physx.scripts.utils import set_physics_scene_asyncsimrender


class PartDropper:
    def __init__(self) -> None:
        self._cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ['default', 'render'])
        self.container_path = "" 
        self.part_path = "" 
        self.part_size = Gf.Vec3f()
        self.container_path = ""
        self.container_size = Gf.Vec3f()
        self.part_count = 0 
        
    def can_create_container(self) -> bool:
        return self.container_path != ""

    def can_create_parts(self) -> bool:
        return self.can_create_container() and self.part_path != ""

    def bounds(self, usd_path) -> Gf.Range3d:
        stage = Usd.Stage.Open(usd_path)
        bounds = self._cache.ComputeWorldBound(stage.GetPrimAtPath("/"))
        stage = None 
        return bounds.GetRange()

    def set_container_usd(self, usd_path):
        self.container_path = usd_path
        self.container_size = self.bounds(usd_path).GetSize()

        
    def set_part_usd(self, usd_path):
        self.part_path = usd_path
        self.part_bounds= self.bounds(usd_path)
        self.part_size = self.part_bounds.GetSize()

    
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

        add_ground_plane(stage, "/World/PartDropper/GroundPlane", "Z", 750.0, Gf.Vec3f(0.0, 0.0, 0), Gf.Vec3f(0.5))

    def create_container(self, stage: Usd.Stage):
        bbox = self.bounds(self.container_path)
        pcenter = bbox.GetMidpoint()
        pmin = bbox.GetMin()
        psize = bbox.GetSize()
        
        stage.RemovePrim("/World/PartDropper/Container")
        box_prim = stage.DefinePrim("/World/PartDropper/Container") 
        box_prim.GetReferences().AddReference(self.container_path)
        self._box_offset = Gf.Vec3f(-pcenter[0], -pcenter[1], -pmin[2])
        UsdGeom.Xformable(box_prim).AddTranslateOp().Set(self._box_offset)

        UsdPhysics.CollisionAPI.Apply(box_prim)
        
        mesh_api = UsdPhysics.MeshCollisionAPI.Apply(box_prim)

    def add_part(self, stage: Usd.Stage):
        self.part_count += 1 
        
        part_prim = stage.DefinePrim(f"/World/PartDropper/Parts/Part_{self.part_count}", "Xform")
        part_prim.GetReferences().AddReference(self.part_path)
        
        UsdPhysics.CollisionAPI.Apply(part_prim) 
        physicsAPI = UsdPhysics.RigidBodyAPI.Apply(part_prim)        
        c = self.part_bounds.GetMidpoint()
        UsdGeom.Xformable(part_prim).AddTranslateOp().Set(Gf.Vec3f(-c[0], -c[1], 50))