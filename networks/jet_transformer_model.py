import numpy as np
import math
import torch
from torch import Tensor
from nn.model.JetTransformer import JetTransformerTagger

def get_model(data_config, **kwargs):

    ## number of classes
    num_classes = len(data_config.label_value)
    
    ## options                                                                                                                                                                                   
    cfg = dict(
        ## input tensor dimensions
        jet_input_dim = len(data_config.input_dicts['jet_features']),
        jet_pair_input_dim = len(data_config.input_dicts['jet_pair_features']),
        ## output dimensions
        num_classes = num_classes,
        ## embeddings
        embed_dims = [64, 64],
        pair_embed_dims = [32, 32],
        pair_input_dim = 9,
        ## transformer parameters
        block_params = None,
        num_heads = kwargs.get('num_heads',4),
        num_layers = kwargs.get('num_layers',4),
        num_cls_layers = kwargs.get('num_cls_layers',2),
        cls_block_params={'dropout': 0.05, 'attn_dropout': 0.05, 'activation_dropout': 0.05},
        ## other options
        remove_self_pair = kwargs.get('remove_self_pair',True),
        use_pre_activation_pair = kwargs.get('use_pre_activation_pair',True),
        activation = kwargs.get('activation','gelu'),
        trim = kwargs.get('use_trim',True),
        use_amp = kwargs.get('use_amp',False),
        ## final dense layers (nodes, dropout)
        fc_params = [(64, 0.1), (32, 0.1), (16,0.1)]
    );

    model = JetTransformerTagger(**cfg)
    
    model_info = {
        'input_names':list(data_config.input_names),
        'input_shapes':{k:((1,) + s[1:]) for k, s in data_config.input_shapes.items()},
        'output_names':['output'],
        'dynamic_axes':{**{k:{0:'N', 2:'n_' + k.split('_')[0]} for k in data_config.input_names}, **{'output':{0:'N'}}},
        }

    return model, model_info

####
class CrossEntropyWeightLoss(torch.nn.L1Loss):
    __constants__ = ['reduction','class_weight']

    def __init__(self, 
                 reduction: str = 'mean',
                 class_weight: list = []
             ) -> None:
        super(CrossEntropyWeightLoss, self).__init__(None, None, reduction)
        self.class_weight = class_weight;
        
    def forward(self, input_cat: Tensor, y_cat: Tensor, y_weight: Tensor) -> Tensor:
        loss_cat = torch.nn.functional.cross_entropy(input_cat,y_cat,weight=self.class_weight,reduction='none');
        loss_cat = loss_cat*y_weight;
        if self.reduction == "mean":
            return loss_cat.mean();
        elif self.reduction == "sum":
            return loss_cat.sum();
        else:
            return loss_cat
                        
def get_loss(data_config, **kwargs):
    class_weight = data_config.label_class_weight;
    return CrossEntropyWeightLoss(
        reduction=kwargs.get('reduction','mean'),
        class_weight=class_weight
    );