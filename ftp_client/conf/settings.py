#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author  :  smx
@file    :  settings.py
@time    :  2021/7/15 10:35
"""


status_code = {
    '100': {'desc': 'Continue', 'status': True},
    '100.1': {'desc': 'Type your username please', 'status': True},
    '100.2': {'desc': 'Type your password please', 'status': True},
    '100.3': {'desc': 'Type your password once again to confirm', 'status': True},
    '200': {'desc': 'OK', 'status': True},
    '202': {'desc': 'Accepted', 'status': True},
    '205': {'desc': 'Reset content', 'status': False},
    '400': {'desc': 'Bad request', 'status': False},
    '401': {'desc': 'Unauthorized', 'status': False},
    '403.3': {'desc': 'Write forbidden', 'status': False},
    '404': {'desc': 'Not found', 'status': False},
    '404.0': {'desc': 'User not exist', 'status': False},
    '409': {'desc': 'Conflict', 'status': False},
    '410': {'desc': 'Gone', 'status': False}
}