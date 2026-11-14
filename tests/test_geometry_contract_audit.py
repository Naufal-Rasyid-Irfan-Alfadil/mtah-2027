"""Synthetic checks for the audit's syntax inspection and algebra; no dataset I/O."""
import importlib.util
import io
from pathlib import Path
import unittest

import cv2
import numpy as np

spec = importlib.util.spec_from_file_location('geometry_audit',
    Path(__file__).resolve().parents[1]/'tools/audit_geometry_contract.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class GeometryAuditTests(unittest.TestCase):
    def test_reads_three_literals_without_unpickling(self):
        stream = io.BytesIO()
        np.save(stream, np.array([[[.1],[.2],[.3]]], dtype=object))
        stream.seek(0)
        np.testing.assert_array_equal(audit.static_pose_literals(stream), [[.1],[.2],[.3]])

    def test_unexpected_shape_or_nonfinite_literals_rejected(self):
        for values in (np.zeros((1,4,1),dtype=object),
                       np.array([[[float('nan')],[.2],[.3]]],dtype=object)):
            stream = io.BytesIO()
            np.save(stream, values)
            stream.seek(0)
            with self.assertRaises(ValueError):
                audit.static_pose_literals(stream)

    def test_derived_H_and_direct_pose_are_same_fixed_camera(self):
        k = np.array([[800.,0,640],[0,800,360],[0,0,1]])
        d = np.array([.01,-.001,0,0])
        rv = np.array([[.1],[.2],[.03]])
        tv = np.array([[1.],[2.],[100.]])
        world = np.array([[0.,0],[10.,20],[50.,60]])
        h = audit.fixed_pose_homography(k, rv, tv)
        und = cv2.perspectiveTransform(world.reshape(-1,1,2),h)
        rays = cv2.perspectiveTransform(und,np.linalg.inv(k))
        from_h = cv2.fisheye.distortPoints(rays,k,d)
        direct = cv2.fisheye.projectPoints(np.c_[world,np.zeros(3)].reshape(-1,1,3),rv,tv,k,d)[0]
        np.testing.assert_allclose(from_h,direct,rtol=0,atol=1e-9)


if __name__ == '__main__':
    unittest.main()
