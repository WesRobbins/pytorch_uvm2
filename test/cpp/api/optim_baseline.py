"""Script to generate baseline values from PyTorch optimization algorithms"""

import argparse
import math

import torch
import torch.optim


HEADER = """
#include <ATen/ATen.h>

#include <vector>

namespace expected_parameters {
"""

FOOTER = "} // namespace expected_parameters"

PARAMETERS = "static std::vector<std::vector<at::Tensor>> {} = {{"

OPTIMIZERS = {
    "Adam": lambda p: torch.optim.Adam(p, 1.0, weight_decay=1e-6),
    "Adagrad": lambda p: torch.optim.Adagrad(p, 1.0, weight_decay=1e-6, lr_decay=1e-3),
    "RMSprop": lambda p: torch.optim.RMSprop(p, 0.1, momentum=0.9, weight_decay=1e-6),
    "SGD": lambda p: torch.optim.SGD(p, 0.1, momentum=0.9, weight_decay=1e-6),
}


def weight_init(module):
    if isinstance(module, torch.nn.Linear):
        stdev = 1.0 / math.sqrt(module.weight.size(1))
        for p in module.parameters():
            p.data.uniform_(-stdev, stdev)


def run(optimizer_name, iterations, sample_every):
    torch.manual_seed(0)
    model = torch.nn.Sequential(
        torch.nn.Linear(2, 3),
        torch.nn.Sigmoid(),
        torch.nn.Linear(3, 1),
        torch.nn.Sigmoid(),
    )
    model = model.to(torch.float64).apply(weight_init)

    optimizer = OPTIMIZERS[optimizer_name](model.parameters())

    input = torch.tensor([[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]], dtype=torch.float64)

    values = []
    for i in range(iterations):
        optimizer.zero_grad()

        output = model.forward(input)
        loss = output.sum()
        loss.backward()

        optimizer.step()

        if i % sample_every == 0:

            values.append(
                [p.clone().flatten().data.numpy() for p in model.parameters()]
            )

    return values


def emit(optimizer_parameter_map):
    # Don't write generated with an @ in front, else this file is recognized as generated.
    print("// @{} from {}".format('generated', __file__))
    print(HEADER)
    for optimizer_name, parameters in optimizer_parameter_map.items():
        print(PARAMETERS.format(optimizer_name))
        for sample in parameters:
            print("  {")
            for parameter in sample:
                parameter_values = "{{{}}}".format(", ".join(map(str, parameter)))
                print("      at::tensor({}),".format(parameter_values))
            print("  },")
        print("};\n")
    print(FOOTER)


def main():
    parser = argparse.ArgumentParser(
        "Produce optimization output baseline from PyTorch"
    )
    parser.add_argument("-i", "--iterations", default=1001, type=int)
    parser.add_argument("-s", "--sample-every", default=100, type=int)
    options = parser.parse_args()

    optimizer_parameter_map = {}
    for optimizer in ["Adam", "Adagrad", "RMSprop", "SGD"]:
        optimizer_parameter_map[optimizer] = run(
            optimizer, options.iterations, options.sample_every
        )

    emit(optimizer_parameter_map)


if __name__ == "__main__":
    main()
