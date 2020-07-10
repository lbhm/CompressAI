from typing import Union, Tuple

import torch
import torch.nn.functional as F

from torch import Tensor

YCBCR_WEIGHTS = {
    # Spec: (K_r, K_g, K_b) with K_g = 1 - K_r - K_b
    'ITU-R_BT.709': (0.2126, 0.7152, 0.0722)
}


def _check_input_tensor(tensor: Tensor) -> None:
    if not isinstance(tensor, Tensor) or \
            not tensor.is_floating_point() or \
            not len(tensor.size()) in (3, 4) or \
            not tensor.size(-3) == 3:
        raise ValueError('Expected a 4D tensor with shape (Nx3xHxW) as input')


def rgb2ycbcr(rgb: Tensor) -> Tensor:
    """RGB to YCbCr conversion for torch Tensor.
    Use the ITU-R BT.709 coefficients.

    Args:
        rgb (torch.Tensor): 3D or 4D floating point rgb tensor

    Return:
        ycbcr(torch.Tensor): converted tensor
    """
    _check_input_tensor(rgb)

    r, g, b = rgb.chunk(3, -3)
    Kr, Kg, Kb = YCBCR_WEIGHTS['ITU-R_BT.709']
    y = Kr * r + Kg * g + Kb * b
    cb = 0.5 * (b - y) / (1 - Kb) + 0.5
    cr = 0.5 * (r - y) / (1 - Kr) + 0.5
    ycbcr = torch.cat((y, cb, cr), dim=-3)
    return ycbcr


def ycbcr2rgb(ycbcr: Tensor) -> Tensor:
    """YCbCr to RGB conversion for torch Tensor.
    Use the ITU-R BT.709 coefficients.

    Args:
        ycbcr(torch.Tensor): 3D or 4D floating point rgb tensor

    Return:
        rgb(torch.Tensor): converted tensor
    """
    _check_input_tensor(ycbcr)

    y, cb, cr = ycbcr.chunk(3, -3)
    Kr, Kg, Kb = YCBCR_WEIGHTS['ITU-R_BT.709']
    r = y + (2 - 2 * Kr) * (cr - 0.5)
    b = y + (2 - 2 * Kb) * (cb - 0.5)
    g = (y - Kr * r - Kb * b) / Kg
    rgb = torch.cat((r, g, b), dim=-3)
    return rgb


def yuv_444_to_420(
    yuv: Union[Tensor, Tuple[Tensor, Tensor, Tensor]]
) -> Tuple[Tensor, Tensor, Tensor]:
    """Convert a 444 tensor to a 420 representation.
    """
    def _downsample(tensor):
        return F.avg_pool2d(tensor, kernel_size=2, stride=2)

    if isinstance(yuv, torch.Tensor):
        y, u, v = yuv.chunk(3, 1)
    else:
        y, u, v = yuv

    return (y, _downsample(u), _downsample(v))


def yuv_420_to_444(yuv: Tuple[Tensor, Tensor, Tensor],
                   return_tuple: bool = False
                   ) -> Union[Tensor, Tuple[Tensor, Tensor, Tensor]]:
    """Convert a 420 tensor to a 444 representation.

    Args:
        yuv (tuple(Tensor, Tensor, Tensor)): 420 input frames
        return_tuple (bool): return input as tuple of tensors instead of a
        concatenated tensor (default: False)
    """
    if len(yuv) != 3 or \
            any(not isinstance(c, torch.Tensor) for c in yuv):
        raise ValueError('Expected a tuple of 3 torch tensors')

    def _upsample(tensor):
        return F.interpolate(tensor,
                             scale_factor=2,
                             mode='bilinear',
                             align_corners=False)

    y, u, v = yuv
    u, v = _upsample(u), _upsample(v)
    if return_tuple:
        return y, u, v
    return torch.cat((y, u, v), dim=1)