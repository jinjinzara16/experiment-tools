#!/usr/bin/env python3

import os
import socket
import struct
import csv

import torch
import torch.nn as nn
import torch.optim as optim

SOCK_PATH = os.environ.get("AFL_RL_SOCK", "/tmp/afl_rl.sock")
STATE_DIM = 8
N_ACTIONS = 4

MSG_FMT = "d" + "d" * STATE_DIM
RESP_FMT = "i"

LR = float(os.environ.get("RL_LR", "1e-4"))
GAMMA = float(os.environ.get("RL_GAMMA", "0.99"))
CLIP = float(os.environ.get("RL_CLIP", "0.2"))

print(f"[PPO] Hyperparams: LR={LR}, GAMMA={GAMMA}, CLIP={CLIP}", flush=True)

LOG_CSV = "ppo_log.csv"
csv_f = open(LOG_CSV, "w", newline="")
csv_writer = csv.writer(csv_f)
csv_writer.writerow(["step", "reward", "a0", "a1", "a2", "a3"])
csv_f.flush()


def log_step(step, reward, actions):

    row = [step, reward] + list(actions)
    csv_writer.writerow(row)
    csv_f.flush()


class PolicyNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(STATE_DIM, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, N_ACTIONS),
        )

    def forward(self, x):
        return self.net(x)


class ValueNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(STATE_DIM, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
        )

    def forward(self, x):
        return self.net(x)


def main():
    if os.path.exists(SOCK_PATH):
        os.unlink(SOCK_PATH)

    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.bind(SOCK_PATH)
    s.listen(1)
    print(f"[PPO] Listening on {SOCK_PATH}", flush=True)

    conn, _ = s.accept()
    print("[PPO] Client connected", flush=True)

    policy = PolicyNet()
    value = ValueNet()
    opt_p = optim.Adam(policy.parameters(), lr=LR)
    opt_v = optim.Adam(value.parameters(), lr=LR)

    msg_size = struct.calcsize(MSG_FMT)

    last_state = None
    last_action = None

    action_hist = [0 for _ in range(N_ACTIONS)]
    step_counter = 0

    try:
        while True:
            buf = b""
            while len(buf) < msg_size:
                chunk = conn.recv(msg_size - len(buf))
                if not chunk:
                    print("[PPO] EOF from client", flush=True)
                    return
                buf += chunk

            unpacked = struct.unpack(MSG_FMT, buf)
            reward_prev = unpacked[0]
            state_vec = unpacked[1:]

            state = torch.tensor(state_vec, dtype=torch.float32).unsqueeze(0)

            if last_state is not None and last_action is not None:
                with torch.no_grad():
                    v_next = value(state)

                v = value(last_state)
                td_target = reward_prev + GAMMA * v_next
                advantage = (td_target - v).detach()

                v_loss = (td_target - v).pow(2).mean()
                opt_v.zero_grad()
                v_loss.backward()
                opt_v.step()

                logits_old = policy(last_state)
                probs_old = torch.softmax(logits_old, dim=-1)
                prob_a_old = probs_old[0, last_action].detach()

                logits_new = policy(last_state)
                probs_new = torch.softmax(logits_new, dim=-1)
                prob_a_new = probs_new[0, last_action]

                ratio = prob_a_new / (prob_a_old + 1e-8)
                surr1 = ratio * advantage
                surr2 = torch.clamp(ratio, 1.0 - CLIP, 1.0 + CLIP) * advantage
                p_loss = -torch.min(surr1, surr2)

                opt_p.zero_grad()
                p_loss.backward()
                opt_p.step()

            with torch.no_grad():
                logits = policy(state)
                probs = torch.softmax(logits, dim=-1)
                dist = torch.distributions.Categorical(probs)
                action = dist.sample().item()

            if 0 <= action < N_ACTIONS:
                action_hist[action] += 1
            else:
                print(f"[PPO] WARNING: invalid action {action}", flush=True)

            step_counter += 1

            probs_list = probs[0].tolist()
            log_step(step_counter, reward_prev, probs_list)

            if step_counter % 100 == 0:
                print(f"[PPO] step={step_counter}, actions={action_hist}", flush=True)

            last_state = state
            last_action = action

            resp = struct.pack(RESP_FMT, int(action))
            conn.sendall(resp)

    except KeyboardInterrupt:
        print("\n[PPO] KeyboardInterrupt, shutting down.", flush=True)

    finally:
        print("[PPO] FINAL actions hist:", action_hist, flush=True)
        try:
            csv_f.flush()
            csv_f.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
        try:
            s.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
