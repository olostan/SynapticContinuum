"""Tiny event-driven recurrent communication experiment. Requires PyTorch (CPU works).

No autoregressive text-token decoding happens inside the network. Characters enter
as brief external events. The recurrent substrate updates at every internal tick,
including silent ticks, using short- and long-memory traces. A two-unit communication
readout emits discrete events, whose occurrence is fed back on the next tick.

This is a *toy supervised demonstration*, not evidence of autonomous cognition.
"""
import argparse
import random

import torch
from torch import nn
import torch.nn.functional as F

ALPHABET = "HIBYE"
OUT = ["HELLO", "GOODBYE"]

class NeuralField(nn.Module):
    def __init__(self, n=48):
        super().__init__()
        self.n = n
        self.input = nn.Linear(len(ALPHABET) + len(OUT), n, bias=False)
        self.recurrent = nn.Linear(n, n, bias=False)
        self.fast = nn.Linear(n, n, bias=False)
        self.slow = nn.Linear(n, n, bias=False)
        self.bias = nn.Parameter(torch.zeros(n))
        self.communication = nn.Linear(n, len(OUT))
        nn.init.orthogonal_(self.recurrent.weight, gain=0.6)
        nn.init.normal_(self.fast.weight, 0, 0.015)
        nn.init.normal_(self.slow.weight, 0, 0.015)
        nn.init.constant_(self.communication.bias, -2.5)

    def run(self, external, feedback=None):
        """external [T,B,5] holds event pulses; silent ticks contain zeros."""
        T, B, _ = external.shape
        h = external.new_zeros(B, self.n)
        fast = torch.zeros_like(h)
        slow = torch.zeros_like(h)
        prev_comm = external.new_zeros(B, len(OUT))
        armed = torch.ones(B, len(OUT), dtype=torch.bool)
        logits_seq = []
        for t in range(T):
            x = torch.cat([external[t], prev_comm], dim=-1)
            h_next = torch.tanh(
                0.72 * h + 0.34 * self.recurrent(h)
                + 0.13 * self.fast(fast) + 0.13 * self.slow(slow)
                + self.input(x) + self.bias
            )
            fast = 0.63 * fast + 0.37 * h_next
            slow = 0.95 * slow + 0.05 * h_next
            h = h_next
            logits = self.communication(h)
            logits_seq.append(logits)
            if feedback is not None:
                prev_comm = feedback[t]  # teacher-forced outgoing event during training
            else:
                p = torch.sigmoid(logits)
                high = p > 0.75
                prev_comm = (high & armed).float()
                armed = (armed & ~high) | (p < 0.30)
        return torch.stack(logits_seq)


def generate_batch(batch=48, T=20, seed=None):
    if seed is not None:
        random.seed(seed)
    external = torch.zeros(T, batch, len(ALPHABET))
    target = torch.zeros(T, batch, len(OUT))
    desc = []
    for b in range(batch):
        kind = random.choice(["HI", "BYE", "H", "B", "", "HI", "BYE"])
        t = random.randint(1, 3)
        for ch in kind:
            external[t, b, ALPHABET.index(ch)] = 1.0
            t += random.choice([1, 2, 3])
        if kind == "HI":
            target[min(T-1, t+2), b, 0] = 1.0
        elif kind == "BYE":
            target[min(T-1, t+2), b, 1] = 1.0
        desc.append(kind or "[silence]")
    return external, target, desc


def train(model, epochs=420, batch=48):
    optim = torch.optim.Adam(model.parameters(), lr=0.005)
    for step in range(epochs):
        inp, target, _ = generate_batch(batch)
        logits = model.run(inp, feedback=target)
        loss = F.binary_cross_entropy_with_logits(
            logits, target, pos_weight=torch.tensor([18., 18.])
        )
        optim.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optim.step()
        if (step+1) % 100 == 0 or step == 0:
            print(f"training step {step+1:>3}/{epochs} loss={loss.item():.4f}")


def observe(model, word, times=None, T=21):
    x = torch.zeros(T, 1, len(ALPHABET))
    if times is None:
        times = list(range(2, 2+2*len(word), 2))
    for t, ch in zip(times, word):
        x[t, 0, ALPHABET.index(ch)] = 1
    with torch.no_grad():
        probs = torch.sigmoid(model.run(x))[:, 0]
    events = []
    armed = [True]*len(OUT)
    for t, row in enumerate(probs):
        for k, p in enumerate(row):
            if armed[k] and p.item() > 0.75:
                events.append((t, OUT[k], round(p.item(), 3)))
                armed[k] = False
            if p.item() < 0.3:
                armed[k] = True
    print(f"\ninput={word!r}, event times={times}, output events={events or '[silence]'}")
    print("time  input  HELLO GOODBYE")
    for t in range(T):
        inp = ''.join(ch for i, ch in enumerate(ALPHABET) if x[t, 0, i] > 0)
        print(f"{t:>3}   {inp or '.':>3}   {probs[t, 0]:5.2f}   {probs[t, 1]:5.2f}")
    return events


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--steps', type=int, default=420)
    parser.add_argument('--save', default='')
    args = parser.parse_args()
    torch.set_num_threads(1)
    random.seed(13)
    torch.manual_seed(13)
    model = NeuralField()
    print('Training continuous-activation field, not an autoregressive LM.')
    train(model, args.steps)
    model.eval()
    observe(model, 'HI')
    observe(model, 'BYE')
    observe(model, 'H')
    observe(model, '', [])
    observe(model, 'HI', [2, 8])
    if args.save:
        torch.save({'model': model.state_dict(), 'seed': 13}, args.save)
        print('Saved:', args.save)


if __name__ == '__main__':
    main()
