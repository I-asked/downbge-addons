from __future__ import absolute_import
import bpy
op = bpy.context.active_operator

op.x_eq = '(1-0.1*cos(v))*cos(u)'
op.y_eq = '0.1*(sin(v) + u/1.7 -10)'
op.z_eq = '(1-0.1*cos(v))*sin(u)'
op.range_u_min = 0.0
op.range_u_max = 12.566370964050293
op.range_u_step = 128
op.wrap_u = False
op.range_v_min = 0.0
op.range_v_max = 6.2831854820251465
op.range_v_step = 128
op.wrap_v = False
op.close_v = False
op.n_eq = 1
op.a_eq = '0'
op.b_eq = '0'
op.c_eq = '0'
op.f_eq = '0'
op.g_eq = '0'
op.h_eq = '0'
