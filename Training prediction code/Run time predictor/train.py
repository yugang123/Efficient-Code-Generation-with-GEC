# coding=utf-8

import os

from numpy import mean

import transformers
import torch
import json
import random
import numpy as np
import argparse

from torch import tensor
# from torch.utils.tensorboard import SummaryWriter
from datetime import datetime
from tqdm import tqdm
from torch.nn import DataParallel
import logging
from transformers import GPT2Config, GPT2LMHeadModel
from transformers import BertTokenizer
from os.path import join, exists
from itertools import zip_longest, chain

from torch.utils.data import Dataset, DataLoader
from torch.nn import CrossEntropyLoss
from sklearn.model_selection import train_test_split

from model import Model
from train_Dataset import TrainDatasetClass
from test_Dataset import Test_set_Dataset_class
from Predictive_generation_code import Predictive_code_generation_class


tokenVocabulary = transformers.GPT2Tokenizer.from_pretrained("GPT_Token/", pad_token="[PAD]", cls_token="[CLS]")


# ##################################################################### args ######################################
def get_args():

    # ----------------------------------- 命令行解析模块 -----------#
    parser = argparse.ArgumentParser()

    parser.add_argument('--device', default='0', type=str, required=False, help='设置使用哪些显卡')  # 0,1
    parser.add_argument('--no_cuda', action='store_true', help='不使用GPU进行训练')

    parser.add_argument('--arch', default="EleutherAI/gpt-neo-125M", help='model参数')


    parser.add_argument('--log_path', default='log/TrainLog.txt', type=str, required=False, help='训练logger存放位置')

    parser.add_argument('--epochs', default=30, type=int, required=False, help='训练的轮次')
    parser.add_argument('--batch_size', default=1, type=int, required=False, help='训练batch size')  # 8
    parser.add_argument('--gradient_accumulation', default=32, type=int, required=False, help='梯度积累')

    parser.add_argument('--lr', default=1.5e-3, type=float, required=False, help='学习率')
    parser.add_argument('--warmup_steps', default=2000, type=int, required=False, help='warm up步数')
    parser.add_argument('--log_step', default=100, type=int, required=False, help='多少步汇报一次loss')
    parser.add_argument('--max_grad_norm', default=1.0, type=float, required=False)

    parser.add_argument('--Generated_models', default='Generated_models', type=str, required=False, help='Generated_models')
    parser.add_argument('--Whether_to_use_trained_local_mods', default=0, type=str, required=False, help='0为否，1为是')

    parser.add_argument('--seed', type=int, default=666, help='设置种子用于生成随机数，以使得训练的结果是确定的')  # None
    parser.add_argument('--num_workers', type=int, default=5, help="dataloaderload数据时使用的线程数量")

    # --------------------------- 解析参数 ------------------#
    args = parser.parse_args()

    return args


# ##################################################################### 随机种子函数 ####################################
def set_random_seed_function(args):
    """
    设置训练的随机种子
    """
    torch.manual_seed(args.seed)
    random.seed(args.seed)
    np.random.seed(args.seed)

    if args.cuda:
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


# ##################################################################### logger文件 ######################################
def create_log_file_function(args):
    """
    将loggeroutput到logger文件和console
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # ----------------------- 格式 ---------------------#
    time_Format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # ------------------- 创建一个handler，用于写入 logger文件 ---------------#
    file_handler = logging.FileHandler(filename=args.log_path)
    file_handler.setFormatter(time_Format)
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)

    # ------------------- 创建一个handler，用于将loggeroutput到 console（console） -----------#
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(time_Format)
    logger.addHandler(console)

    return logger


# ##################################################################### 创建model ######################################
def create_model(args):

    model = Model(args)

    # --------------------------------- 根据tokenizer的vocabulary 调整 GPT2model的voca的大小 --------#
    # model.resize_token_embeddings(词表词数)

    return model


def complementary_fill_function(A_batch_data):
    """
    计算该batch中的所有sample的最长的input，并且将其他input的长度向其对齐
    :param A_batch_data:
    :return:
    title,problem_Description_Subject,Input_Description,Output_Description,输入output样例测试,Note描述, certain_slow_code, label_code
    """
    code = []
    Running_time = []
    Total_running_time = []

    # ------------------------------- 计算该batch中input的最大长度 --------------------------#
    for a_data in A_batch_data:
        code.append(a_data[0])
        Running_time.append(a_data[1])


    # ---------------------------------------------------------- 转化为张量字典 --------------------------------#
    code_dictionary = tokenVocabulary(code, max_length=768, truncation=True, padding=True, return_tensors="pt")

    Total_running_time.append(Running_time)
    Running_time_tensor = torch.Tensor(Total_running_time)


    return [code_dictionary, Running_time_tensor]


# ##################################################################### 训练函数 #######################################
def train_Functions(model, devices, Training_set_data, test_set_data, Multiple_GPUs, args):

    # ---------------------------- 将 train_data 为 train_dataloader --------------------#
    train_dataloader = DataLoader(dataset=Training_set_data,  # 使用的Dataset
                         batch_size=args.batch_size,  # 批处理样本大小
                         shuffle=True,  # 每次迭代前打乱数据
                         num_workers=args.num_workers,  # 使用一个进程
                         collate_fn=complementary_fill_function
                         )

    # ------------- 进入训练状态 --------#
    model.train()

    # ------------------------------- 计算所有epoch进行参数优化的Total_number_stepstotal_steps ---------------------------#
    Total_number_steps = int(train_dataloader.__len__() * args.epochs / args.batch_size / args.gradient_accumulation)

    # ------------------------- 写入logger ------------------------#
    logger.info(f'-------- Total_number_steps：total training steps = {Total_number_steps} ---------')

    # ---------------------- 设置Optimizer，并且在初始训练时，使用 warm up 策略 ---------------------#
    Optimizer = transformers.AdamW(model.parameters(), lr=args.lr, correct_bias=True)
    # scheduler = transformers.WarmupLinearSchedule(Optimizer, warmup_steps=args.warmup_steps, t_total=Total_number_steps)

    # =============================================================== 均方根误差loss_function ======================================
    loss_function = torch.nn.MSELoss()

    # --------------------------------------- 写入logger --------------------------------#
    logger.info('####################### 开始训练：starting training ###################')

    # ------------------ 用于统计每次梯度累计的loss -------#
    Losses_accumulated_per_gradient = 0

    # ############################################## 开始训练 ################################### #
    for epoch in range(args.epochs):

        # --------- start_time ------------#
        start_time = datetime.now()

        # ----------- 记录 out of memory的次数 -------#
        GPU_memory_shortage_times = 0

        # ------------------- dataloader循环迭代 -------------#
        Training_loss_list = []
        # ---------- Feature_List：title,problem_Description_Subject,Input_Description,Output_Description,输入output样例测试,Note描述, certain_slow_code, label_code -------#
        for Batch_index, [code_dictionary, Running_time_tensor] in enumerate(train_dataloader):

            # GPT2Model的输入为n个token_id时，output也是n个hidden_state，使用第n个hidden_state预测第n+1个token

            # ----------------------------- 移动到GPU -------------------------------#
            code_dictionary["input_ids"] = code_dictionary["input_ids"].to(devices)
            code_dictionary["attention_mask"] = code_dictionary["attention_mask"].to(devices)
            Running_time_tensor = Running_time_tensor.to(devices)
            try:
                code_dictionary["token_type_ids"] = code_dictionary["token_type_ids"].to(devices)
            except:
                pass

            # --------------- 解决在运行过程中，由于显存不足产生的cuda out of memory的问题 ---------------#
            try:
                # model_output = model.forward(input_ids=特征)
                model_output = model(code_dictionary)

                # ================================================= 均方根误差loss_function =====================================
                loss = loss_function(model_output, Running_time_tensor)

                # ---------------------------- 累积loss ------------------------#
                Training_loss_list.append(loss.item())

                # ------------------------------- 更新logger与tnesorboardX信息 --------------------------------------#
                if Batch_index % args.log_step == 0:
                    logger.info(f'\033[0:32m第 {epoch+1} 轮(共{args.epochs}轮)，第 {Batch_index+1} 批数据(共{len(train_dataloader)}批), loss： {loss:.3f}\033[m')

                # -------------- 如果是多个GPU，均值 -------------#
                if Multiple_GPUs:
                    loss = loss.mean()

                # -------------- 如果是梯度累积，相除 -------------#
                if args.gradient_accumulation > 1:
                    loss = loss / args.gradient_accumulation

                # -------------- 梯度反向传播 --------#
                loss.backward()

                # ---------------------- 梯度裁剪：解决的是梯度消失或爆炸的问题，即设定阈值 -----------------#
                torch.nn.utils.clip_grad_norm_(model.parameters(), args.max_grad_norm)

                # ------------------ 进行一定step的梯度累计之后，更新参数 --------------#
                if (Batch_index + 1) % args.gradient_accumulation == 0:
                    Losses_accumulated_per_gradient += loss.item()
                    # ---------------- 更新参数 -------#
                    Optimizer.step()
                    # ---------------- 清空梯度信息 -----#
                    Optimizer.zero_grad()
                    # ---------------- 进行warm up -----#
                    # scheduler.step()

            # ============================= 解决在运行过程中，由于显存不足产生的cuda out of memory的问题 ===================#
            except RuntimeError as exception:
                if "out of memory" in str(exception):
                    GPU_memory_shortage_times += 1
                    logger.info(f"#======== WARNING: GPU_memory_shortage_times：ran out of memory,times: {GPU_memory_shortage_times} ========#")
                    if hasattr(torch.cuda, 'empty_cache'):
                        torch.cuda.empty_cache()
                else:
                    logger.info(str(exception))
                    raise exception

            break

        # ========================== epoch训练结束 ================#
        Ending_time = datetime.now()

        # ======================================================== 每结束一轮，保存model一次 ============================#
        torch.save(model.Fully_connected_layer, "./Generated_models/Fully_connected_layer.pkl")
        model.Code_Layer.save_pretrained(f"./Generated_models/Code_Layer/")

        # ----------------------------------------------- 写入logger ----------------------------------------------------#
        logger.info(f'\033[0:34m===== 训练集,第 {epoch+1} 轮结束，平均loss：{mean(Training_loss_list)}。model已经保存。Total_running_time：{Ending_time - start_time} =======\033[m')

        # ------------------------------- 测试model ------------------#
        test_average_loss = predictive_Functions(model, devices, test_set_data, Multiple_GPUs, args)

        break

    # ------------------------------------------ 训练结束：写入logger ------------------------------------------------#
    # log.info(f'\033[0:34m======================= 结束 training finishedtest_average_loss：{test_average_loss} ============\033[m')
    logger.info(f'\033[0:35m################## 结束。训练平均loss：{mean(Training_loss_list)}。test_average_loss：{test_average_loss} ###################\033[m')


# ##################################################################### predictive_Functions #######################################
def predictive_Functions(model, devices, test_set_data, Multiple_GPUs, args):
    # -------------------------------------- 开始预测：写入logger -----------------------------#
    logger.info("============================== 开始预测model =================================")

    # =============================================================== 均方根误差loss_function ======================================
    loss_function = torch.nn.MSELoss()

    # -------- 进入预测状态：不计算梯度 --------#
    model.eval()

    # ----------------------------------- 将 test_data 为 test_dataloader --------------------#
    test_dataloader = DataLoader(test_set_data,  # 使用的Dataset
                         batch_size=args.batch_size,  # 批处理样本大小
                         shuffle=True,  # 每次迭代前打乱数据
                         num_workers=args.num_workers,  # 使用一个进程
                         collate_fn=complementary_fill_function
                         )

    # =========================== 无梯度 ======================#
    with torch.no_grad():
        Loss_List = []
        for Batch_index, [code_dictionary, Running_time_tensor] in enumerate(test_dataloader):

            # GPT2Model的输入为n个token_id时，output也是n个hidden_state，使用第n个hidden_state预测第n+1个token

            # ----------------------------- 移动到GPU -------------------------------#
            code_dictionary["input_ids"] = code_dictionary["input_ids"].to(devices)
            code_dictionary["attention_mask"] = code_dictionary["attention_mask"].to(devices)
            Running_time_tensor = Running_time_tensor.to(devices)
            try:
                code_dictionary["token_type_ids"] = code_dictionary["token_type_ids"].to(devices)
            except:
                pass

            # ----------------------------------------------#
            try:
                model_output = model(code_dictionary)
            except:
                continue

            loss = loss_function(model_output, Running_time_tensor)

            # ---------------------------- 累积loss ------------------------#
            Loss_List.append(loss.item())

            break


        # -------------------------------- 预测结果：写入logger -------------------------------------------------#
        logger.info(f'\033[0:32m预测模式:  loss： {mean(Loss_List):.3f}\033[m')

        # --------------------------------------- 结束预测：写入logger --------------------------------------#
        logger.info('\033[0:34m========================== 结束预测 ==================================\033[m')

        return mean(Loss_List)


# ####################################################################### 主函数 #######################################
def main():
    # -------------------------- 初始化args -----#
    args = get_args()

    # -------------------------------- 创建logger对象 -----#
    # ----------- logger同时output到文件和console -------#
    global logger
    logger = create_log_file_function(args)

    # ================================================================ 当用户使用GPU,并且GPU可用时 ===================#
    os.environ['CUDA_VISIBLE_DEVICES'] = '0'
    args.cuda = torch.cuda.is_available() and not args.no_cuda
    devices = 'cuda' if args.cuda else 'cpu'
    # devices = 'cpu'
    logger.info('using devices:{}'.format(devices))
    # 为CPU设置种子用于生成随机数，以使得结果是确定的
    # 为当前GPU设置随机种子；如果使用多个GPU，应该使用torch.cuda.manual_seed_all()为所有的GPU设置种子。
    # 当得到比较好的结果时我们通常希望这个结果是可以复现
    if args.seed:
        set_random_seed_function(args)

    # -------------------------------------------------------- 初始化tokenizer --------------#

    # -------------------- 创建model的output目录 -------------------#
    if not os.path.exists(args.Generated_models):
        os.mkdir(args.Generated_models)

    # --------------------- loadGPTmodel ------------------------#
    model = create_model(args)

    # ------------- 移到GPU ----#
    model.to(devices)

    # -------------------------- 是否使用Multiple_GPUs进行并行运算 ------------------------#
    Multiple_GPUs = False
    if args.cuda and torch.cuda.device_count() > 1:
        logger.info("Let's use 多个 GPUs to 训练")
        model = DataParallel(model, device_ids=[int(i) for i in args.device.split(',')])

    # ------------------------- 记录model参数数量 ---------------#
    Total_number_parameters = 0
    model_parameter_list = model.parameters()
    for a_layer_parameters in model_parameter_list:
        Total_number_parameters += a_layer_parameters.numel()

    # ------------------------------------ log ----------------#
    logger.info(f'=========== model总参数: {Total_number_parameters} =================')

    # -------------------------------- log ---------------------------------#
    logger.info("=================== loadtrain_data。。。 =======================")

    # ============================== load数据 ===============================#
    train_data = TrainDatasetClass()
    test_data = Test_set_Dataset_class()

    # ----------------------------- 开始训练 ------------------------#
    train_Functions(model, devices, train_data,test_data, Multiple_GPUs, args)

    # --------------------------- 预测code生成 ------------------------#
    # Predictive_code_generation = Predictive_code_generation_class()
    # Predictive_code_generation.entrance()

# ############################################################ entrance ####################################################
if __name__ == '__main__':
    main()
