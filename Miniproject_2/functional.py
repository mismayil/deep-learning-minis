from typing import Optional, Union, Tuple
from math import floor

import torch
from torch.nn.functional import fold, unfold


def linear(x: torch.Tensor, weight: torch.Tensor,
           bias: Optional[torch.Tensor] = None) -> torch.Tensor:
    """Apply a linear transformation to the input x

    Args:
        x (torch.Tensor): Input tensor. Must be of shape (*, IN_DIM)
        weight (torch.Tensor): Weight matrix. Must be of shape (OUT_DIM, IN_DIM)
        bias (Optional[torch.Tensor], optional): Bias vector. Must be of shape (OUT_DIM). Defaults to None.

    Returns:
        torch.Tensor: Transformed input
    """
    output = x.mm(weight.T)

    if bias is not None:
        output += bias

    return output


def conv2d(input_: torch.Tensor, kernels: torch.Tensor, padding: int, stride: int,
           dilation: int):
    # input size is (batch_size x channels x height x width)
    N_in, C_in, H_in, W_in = input_.shape

    # kernels are of size (out_channels, in_channels, kernel_height, kernel_width)
    C_out, C_ker, H_ker, W_ker = kernels.shape

    # calculate output shape (based on https://pytorch.org/docs/stable/generated/torch.nn.Conv2d.html)
    H_out = floor((H_in + 2 * padding - dilation * (H_ker - 1) - 1) / stride + 1)
    W_out = floor((W_in + 2 * padding - dilation * (W_ker - 1) - 1) / stride + 1)

    # check whether the number of channels in the input is correct
    if C_in != C_ker: raise ValueError(
        "Numbers of channels in the input and kernel are different.")
    # compute convolutions
    input_unfolded = unfold(input_, kernel_size=(H_ker, W_ker), padding=padding,
                            stride=stride, dilation=dilation)
    kernels_flattened = kernels.reshape(C_out, C_ker * H_ker * W_ker).T

    # print("Shapes: ", input_unfolded.shape, kernels_flattened.shape)
    output = torch.empty(N_in, C_out, H_out, W_out)

    for n in range(N_in):
        for k in range(C_out):
            row = input_unfolded[n].transpose(0, 1).mm(
                kernels_flattened[:, k].unsqueeze(1))
            output[n][k] = row.reshape(H_out, W_out)

    return output


def convtranspose2d(tensor_in, in_channels, out_channels, kernel_size, weight, bias,
                    stride, padding, dilation):
    assert in_channels == tensor_in.shape[1], \
        "in_channels of layer must be equal to in_channels of input tensor"
    batch_size, in_channels, in_height, in_width = tensor_in.shape
    # Take batch last
    for in_dim in range(len(tensor_in.shape) - 1):
        tensor_in = tensor_in.transpose(in_dim, in_dim + 1)
    tensor_in = tensor_in.reshape(in_channels, -1)
    output = weight.reshape(in_channels, -1).T.matmul(tensor_in)
    output_t = output.reshape(out_channels * kernel_size[0] * kernel_size[1],
                              in_height * in_width, batch_size)
    # Transpose to batch first
    for in_dim in range(len(output_t.shape) - 1, 0, -1):
        output_t = output_t.transpose(in_dim, in_dim - 1)
    out_height = (in_height - 1) * stride[0] - 2 * padding[0] + dilation[0] * (
            kernel_size[0] - 1) + 1
    out_width = (in_width - 1) * stride[1] - 2 * padding[1] + dilation[1] * (
            kernel_size[1] - 1) + 1
    output = fold(output_t, (out_height, out_width), kernel_size=kernel_size,
                  dilation=dilation, padding=padding, stride=stride)
    if bias:
        output += bias.reshape(1, -1)
    return output


def relu(x: torch.Tensor) -> torch.Tensor:
    return x.maximum(torch.tensor(0))


def sigmoid(x: torch.Tensor) -> torch.Tensor:
    return x.sigmoid()


def max_pool2d(x: torch.Tensor, kernel_size: Union[int, Tuple],
               stride: Optional[Union[int, Tuple]] = None,
               padding: Union[int, Tuple] = 0, dilation: Union[int, Tuple] = 1):
    kernel_size = (kernel_size, kernel_size) if isinstance(kernel_size,
                                                           int) else kernel_size

    if stride is None:
        stride = kernel_size

    stride = (stride, stride) if isinstance(stride, int) else stride
    padding = (padding, padding) if isinstance(padding, int) else padding
    dilation = (dilation, dilation) if isinstance(dilation, int) else dilation

    N, C, H_in, W_in = x.shape
    H_out = floor((H_in + 2 * padding[0] - dilation[0] * (kernel_size[0] - 1) - 1) /
                  stride[0] + 1)
    W_out = floor((W_in + 2 * padding[1] - dilation[1] * (kernel_size[1] - 1) - 1) /
                  stride[1] + 1)

    channel_outputs = []

    for ch in range(C):
        x_ch_unfolded = unfold(x[:, ch, :, :].unsqueeze(1), kernel_size=kernel_size,
                               stride=stride, dilation=dilation, padding=padding)
        x_ch_max, _ = x_ch_unfolded.max(dim=1, keepdim=True)
        channel_outputs.append(x_ch_max.reshape((N, 1, H_out, W_out)))

    output = torch.cat(channel_outputs, dim=1)

    return output
