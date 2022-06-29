# coding=utf-8
"""
Dataset to be used for APPS Training
"""

import torch
import glob
import logging
import random
import fnmatch

from multiprocessing import Manager
# from multiprocessing.shared_memory import ShareableList

import dataset_lm.util as dsutil
import numpy as np
import gc
import os
import io

import transformers

from dataset_lm.reindent import run as run_reindent
from tqdm import tqdm


import json

# ############################################################# 我的Dataset函数 #####################################
class Predicted_Dataset_Class(torch.utils.data.Dataset):
    def __init__(self, dataset_root_path="Code set to be predicted"):

        self.Tokenized = transformers.GPT2Tokenizer.from_pretrained("GPT_Token/", pad_token="[PAD]", cls_token="[CLS]")

        self.total_Data_List = []  # Should be set in 初始化函数()

        # ================================= 初始化函数（将数据从本地导入） ==================#
        self.initialize_function_from_current_directory(dataset_root_path)

    # =========================================== 初始化函数（将数据从本地导入） =========================================#
    def initialize_function_from_current_directory(self, dataset_root_path):
        """ 从本地导入数据
        返回：
            self.total_Data_List = total_Data_List
        """

        total_Data_List = []

        training_list_sets = os.listdir(f"{dataset_root_path}")
        # ----------------------------------------- 导入数据 ------------------------------------------------------------#
        print('\033[0:34m========================== 导入 训练集 数据中... (具体是 将数据转化为ID) ==================\033[m')
        for i in tqdm(training_list_sets):
        # for i in tqdm(range(2000)):
        #for i in tqdm(range(4)):
            if i.split(",")[1]=="BLEU_score":
                # ----------------------------------------------- 标签 --------------------------------#
                with open(f"{dataset_root_path}/{i}", 'r', encoding='UTF-8') as f:
                    code = f.read()

                # ------------------------------ 加入total_Data_List -----------#
                total_Data_List.append(code)

        print(f'\033[0:35m========================== 已load {len(total_Data_List)} 条 训练集 数据 ==================\033[m')

        self.total_Data_List = total_Data_List


    def __len__(self):
        return len(self.total_Data_List)

    # ========================================= 迭代遍历函数 =========================================#
    def __getitem__(self, index):

        # ----------(title,problem_Description_Subject,Input_Description,Output_Description,输入output样例测试,Note描述, certain_slow_code, label_code, Data_original_path)--------#
        Sample_List = self.total_Data_List[index]

        return Sample_List


def Indent_code_functions(Code_String):
    """
    给定的Code_String，以 Github 的方式 重新缩进它
    Given code string, reindent it in the same way that the Github Dataset was indented
    """
    # --------------------------------- 可变字符串_io.stringIO操作 ---------------------------------#
    Code_String = io.StringIO(Code_String)
    Code_string_after_indentation = io.StringIO()

    run_reindent(
        Code_String,
        Code_string_after_indentation,
        config={
            "dry-run": False,
            "help": False,
            "to": 4,
            "from": -1,
            "tabs": True,
            "encoding": "utf-8",
            "is-tabs": False,
            "tabsize": 4,
            "all-tabs": False
        }
    )

    # ------------------- 获取对象值 ---------------#
    return Code_string_after_indentation.getvalue()
