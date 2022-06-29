
import torch
import glob
import logging
import random
import fnmatch

from multiprocessing import Manager

import dataset_lm.util as dsutil
import numpy as np
import gc
import os
import io

import transformers

from dataset_lm.reindent import run as run_reindent
from tqdm import tqdm


import json

class Test_set_Dataset_class(torch.utils.data.Dataset):
    def __init__(self,  dataset_root_path="../../ECG/test"):



        self.Tokenized = transformers.GPT2Tokenizer.from_pretrained("GPT_Token/", pad_token="[PAD]", cls_token="[CLS]")

        self.total_Data_List = []  

        self.initialize_function_from_current_directory(dataset_root_path)

    def initialize_function_from_current_directory(self, dataset_root_path):

        total_Data_List = []

        training_list_sets = os.listdir(f"{dataset_root_path}")
        for i in tqdm(range(len(training_list_sets))):

            with open(f"{dataset_root_path}/{i}/accepted.txt", 'r', encoding='UTF-8') as f:
                label_code = f.read()

            label_code_dictionary = self.Tokenized(label_code, return_tensors="pt")
            if len(label_code_dictionary["input_ids"][0])>766:
                continue

            label_code = Indent_code_functions(label_code)

            with open(f"{dataset_root_path}/{i}/accepted run time.txt", 'r', encoding='UTF-8') as f:
                Running_time = f.read().split("accepted,")[1].split(" ms,")[0]

            Running_time = int(Running_time)
            A_data_tuple = (label_code, Running_time)
            total_Data_List.append(A_data_tuple)


            Slow_code_set_list = os.listdir(f"{dataset_root_path}/{i}/acc_tle_solutions")

            for a_code in Slow_code_set_list:
                with open(f"{dataset_root_path}/{i}/acc_tle_solutions/{a_code}", 'r', encoding='UTF-8') as f:
                    certain_slow_code = f.read()

                certain_slow_code = Indent_code_functions(certain_slow_code)
                certain_slow_code_dictionary = self.Tokenized(certain_slow_code, return_tensors="pt")
                if len(certain_slow_code_dictionary["input_ids"][0]) > 768:
                    continue

                certain_slow_code = Indent_code_functions(certain_slow_code)

                Running_time = int(a_code.split(",")[1].split(" ms")[0])
                A_data_tuple = (certain_slow_code, Running_time)

                total_Data_List.append(A_data_tuple)


            better_code_sets_list = os.listdir(f"{dataset_root_path}/{i}/acc_solutions")

            for a_code in better_code_sets_list:
                with open(f"{dataset_root_path}/{i}/acc_solutions/{a_code}", 'r', encoding='UTF-8') as f:
                    A_better_code = f.read()

                A_better_code = Indent_code_functions(A_better_code)
                A_better_code_dictionary = self.Tokenized(A_better_code, return_tensors="pt")
                if len(A_better_code_dictionary["input_ids"][0]) > 768:
                    continue

                A_better_code = Indent_code_functions(A_better_code)

                Running_time = int(a_code.split(",")[1].split(" ms")[0])
                A_data_tuple = (A_better_code, Running_time)

                total_Data_List.append(A_data_tuple)

        print(f'\033[0:35m========================== load {len(total_Data_List)} ===============\033[m')

        self.total_Data_List = total_Data_List


    def __len__(self):
        return len(self.total_Data_List)

    def __getitem__(self, index):

        Sample_List = self.total_Data_List[index]

        return Sample_List


def Indent_code_functions(Code_String):
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

    return Code_string_after_indentation.getvalue()

