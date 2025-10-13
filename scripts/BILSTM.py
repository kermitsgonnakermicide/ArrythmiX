import torch.nn.functional as F
import torch.nn as nn
import torch


class CNNBiLSTM(nn.Module):
    def __init__(self, input_channels, seq_length, n_classes):
        super(CNNBiLSTM, self).__init__()

        # Store parameters
        self.input_channels = input_channels
        self.seq_length = seq_length
        self.n_classes = n_classes

        # Convolutional layers
        self.conv1 = nn.Conv1d(input_channels, 64, kernel_size=7, padding=3)
        self.bn1 = nn.BatchNorm1d(64)
        self.pool1 = nn.MaxPool1d(2, stride=2)

        self.conv2 = nn.Conv1d(64, 128, kernel_size=5, padding=2)
        self.bn2 = nn.BatchNorm1d(128)
        self.pool2 = nn.MaxPool1d(2, stride=2)

        self.conv3 = nn.Conv1d(128, 256, kernel_size=3, padding=1)
        self.bn3 = nn.BatchNorm1d(256)
        self.pool3 = nn.MaxPool1d(2, stride=2)

        # Calculate LSTM
        self.lstm_input_size = 256
        self.lstm_seq_length = seq_length // 8

        # Bidirectional LSTM
        self.lstm = nn.LSTM(
            input_size=self.lstm_input_size,
            hidden_size=128,
            num_layers=2,
            bidirectional=True,
            batch_first=True,
            dropout=0.3
        )

        # Attention mechanism
        self.attention = nn.MultiheadAttention(
            embed_dim=256,  # 128*2 for bidirectional
            num_heads=8,
            dropout=0.1,
            batch_first=True
        )

        # Fully connected layers
        self.fc1 = nn.Linear(256, 128)  # 128*2 for bidirectional LSTM
        self.dropout1 = nn.Dropout(0.5)
        self.fc2 = nn.Linear(128, 64)
        self.dropout2 = nn.Dropout(0.3)
        self.fc3 = nn.Linear(64, n_classes)

        # Initialize weights
        self._initialize_weights()

    def _initialize_weights(self):
        """Initialize model weights for better training stability"""
        for m in self.modules():
            if isinstance(m, nn.Conv1d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 0.01)
                nn.init.constant_(m.bias, 0)


    def forward(self, x):
        # Input shape: (batch_size, seq_len, features) or (batch_size, features, seq_len)

        # Ensure input is (batch_size, channels, seq_len)
        if x.dim() == 2:
            x = x.unsqueeze(1)  # (batch, 1, seq_len)
        elif x.dim() == 3 and x.size(1) != self.input_channels:
             x = x.permute(0, 2, 1) # Correct permutation to (batch_size, channels, seq_len)


        # Convolutional
        # First conv block
        x = self.conv1(x)
        x = self.bn1(x)
        x = F.relu(x)
        x = self.pool1(x)

        # Second conv block
        x = self.conv2(x)
        x = self.bn2(x)
        x = F.relu(x)
        x = self.pool2(x)

        # Third conv block
        x = self.conv3(x)
        x = self.bn3(x)
        x = F.relu(x)
        x = self.pool3(x)

        # for LSTM: (batch, seq_len, features)
        x = x.permute(0, 2, 1)

        # Bidirectional LSTM
        lstm_out, (hidden, cell) = self.lstm(x)

        # attention mechanism
        attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)

        # Global average pooling
        x = torch.mean(attn_out, dim=1)  # (batch, features)

        # Fully connected
        x = F.relu(self.fc1(x))
        x = self.dropout1(x)
        x = F.relu(self.fc2(x))
        x = self.dropout2(x)
        x = self.fc3(x)

        return x
