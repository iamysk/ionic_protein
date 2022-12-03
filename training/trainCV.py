import torch
import warnings
from torch.utils.data import Dataset, DataLoader
import torch.utils.data as data
import numpy as np
from models import IonicProtein
import torch.nn as nn
from torch.utils.data.sampler import SubsetRandomSampler
import os
from tqdm import tqdm
import pandas as pd

from torch.utils.data import Dataset, DataLoader
import pickle
from sklearn.metrics import f1_score, average_precision_score
import torch.nn.functional as F
from tqdm import trange

from utils import train_loop, ProtEmbDataset

kfolds = 5
model_name = 'esm1_t34_670M_UR50D'
data_path = '/media/dell4/a87d4a0b-5641-40d3-8d10-416948fc2996/ION_DATA/'

for fold in range(1,kfolds+1):
    #count = 0
    print('Training fold', fold)
    train_batches, test_batches = [], []   
    for datapoint in os.listdir(data_path+model_name+'_batch128_CV/'):
        if datapoint.endswith('fold%s.pickle'%(fold)):
            test_batches.append(datapoint)
        elif datapoint.endswith('fold6.pickle'):
            pass
        else:
            train_batches.append(datapoint)
    
    data_list = np.array(os.listdir(data_path+model_name+'_batch128_CV/'))
    train_indices = list(np.where(np.isin(data_list, train_batches))[0])
    test_indices = list(np.where(np.isin(data_list, test_batches))[0])

    #samples_count = len(protein_dataset)
    
    #all_samples_indexes = list(range(samples_count))
    #np.random.shuffle(all_samples_indexes)

    # sampler_train = SubsetRandomSampler(train_batches)
    # sampler_val = SubsetRandomSampler(test_batches)
    # protein_dataset = ProtEmbDatasetCV(model_name)
    # dataloader_train = DataLoader(protein_dataset, batch_size=1, sampler = sampler_train, num_workers=4)
    # dataloader_val = DataLoader(protein_dataset, batch_size=1, sampler = sampler_val, num_workers=4)

    protein_dataset = ProtEmbDataset(model_name)
    sampler_train = SubsetRandomSampler(train_indices)
    sampler_val = SubsetRandomSampler(test_indices)
    dataloader_train = DataLoader(protein_dataset, batch_size=1, sampler = sampler_train, num_workers=4)
    dataloader_val = DataLoader(protein_dataset, batch_size=1, sampler = sampler_val, num_workers=4)

    print('Dataset lengths (train/val):', len(dataloader_train), len(dataloader_val))
    #print(train_indices[0])
    warnings.filterwarnings("ignore")

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = IonicProtein(dataloader_train.dataset[0][0].shape[1]).to(device)

    print('Device:', device)
    #print(model)
    criterion_1 = nn.BCEWithLogitsLoss()
    epochs = 30
    lr = 0.001
    optimizer = torch.optim.Adam(model.parameters(), lr = lr)
    lrsched = torch.optim.lr_scheduler.StepLR(optimizer, 10)
    print('\nTraining model (%s) %s for % epochs at %s learning rate'%('Fold'+str(fold), model_name, epochs, lr))
    net_loss_train, net_f1_train, net_loss_test, net_f1_test = train_loop(model, epochs, dataloader_train, dataloader_val, optimizer, lrsched, criterion_1, 100)
    training_stats = pd.DataFrame()
    training_stats['net_loss_train'] = net_loss_train
    training_stats['net_loss_test'] = net_loss_test
    training_stats['net_f1_train'] = net_f1_train
    training_stats['net_f1_test'] = net_f1_test
    training_stats.to_csv('checkpoints/%s_setB_fold%s.csv'%(model_name, str(fold)))
    torch.save(model.state_dict(), 'checkpoints/%s_setB_fold%s.pt'%(model_name, str(fold)))
    del model