from typing import Tuple
from pathlib import Path

import torch
import os

from utils import psnr
from model import Model

DATA_PATH = 'miniproject_dataset/'
OUTPUT_MODEL_PATH = str(Path(__file__).parent / 'bestmodel.pth')
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')


def get_data(data_path: str = DATA_PATH, mode: str = 'train',
             device: torch.device = torch.device('cpu')) -> \
        Tuple[torch.Tensor, torch.Tensor]:
    """
    Loads the data from the given path.
    """
    if mode == 'train':
        source, target = torch.load(os.path.join(data_path, 'train_data.pkl'),
                                    map_location=device)
    elif mode == 'val':
        source, target = torch.load(os.path.join(data_path, 'val_data.pkl'),
                                    map_location=device)
    else:
        raise ValueError(f'Unknown data type {mode}')
    return source.float() / 255.0, target.float() / 255.0


def train(train_input, train_target, val_input, val_target, num_epochs=100,
          batch_size=64, validation_frequency=1, shuffle_data=True,
          learning_rate=1e-2, wandb_name=None, hidden_dim=16):
    if shuffle_data:
        train_rand_permutation = torch.randperm(train_input.shape[0])
        val_rand_permutation = torch.randperm(val_input.shape[0])
        train_input = train_input[train_rand_permutation]
        train_target = train_target[train_rand_permutation]
        val_input = val_input[val_rand_permutation]
        val_target = val_target[val_rand_permutation]

    if wandb_name is not None:
        import wandb
        wandb.init(project="dl_miniproject2", name=wandb_name,
                   config={"num_epochs": num_epochs, "batch_size": batch_size,
                           "val_freq": validation_frequency,
                           "shuffle_data": shuffle_data,
                           "learning_rate": learning_rate})

    model = Model(learning_rate=learning_rate, hidden_dim=hidden_dim)
    model.set_batch_size(batch_size)
    # OPTIONAL: Set the validation data and frequency
    model.set_val_data(val_input, val_target, validation_frequency=validation_frequency)
    # Train the model
    model.train(train_input, train_target, num_epochs, use_wandb=(wandb_name is not None))
    # Load the pretrained model
    # model.load_pretrained_model(OUTPUT_MODEL_PATH)
    # Evaluate the model
    prediction = model.predict(val_input)
    # Check the PSNR
    psnr_val = psnr(prediction / 255.0, val_target / 255.0, device=DEVICE)
    print(f'PSNR: {psnr_val:.6f} dB')

    if wandb_name is not None:
        wandb.log({"PSNR": psnr_val})

    # Save the best model
    model_path = str(Path(__file__).parent / f'bestmodel_{wandb_name}.pth')
    model.save_pretrained_model(model_path)
    print(f'Saved model to `{model_path}`')
    return model, psnr_val


if __name__ == '__main__':
    train_input, train_target = get_data(mode='train', device=DEVICE)
    val_input, val_target = get_data(mode='val', device=DEVICE)
    model, psnr_val = train(train_input, train_target, val_input, val_target,
                            num_epochs=100, hidden_dim=64, batch_size=32, validation_frequency=10, learning_rate=1e-1)