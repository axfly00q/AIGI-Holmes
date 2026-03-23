import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms
from torch.utils.data import DataLoader
from torchvision.datasets import ImageFolder
from torch.optim import Adam
from PIL import Image
import os

# ==== 1. 配置参数 ====
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print("当前训练设备:", DEVICE)
BATCH_SIZE = 8
LEARNING_RATE = 0.001
NUM_EPOCHS = 5

train_dir = r"data\train"
val_dir   = r"data\val"

# ==== 2. 统计实际目录下文件数量 ====
def count_valid_images(path):
    exts = ('.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG')
    files = [f for f in os.listdir(path) if f.endswith(exts)]
    return len(files)

for phase in ['train', 'val']:
    for cls in ['FAKE', 'REAL']:
        d = f"data\\{phase}\\{cls}"
        if os.path.exists(d):
            print(f"【{phase}/{cls}】图片数量(有效JPG/PNG)：{count_valid_images(d)}")
        else:
            print(f"[警告] 路径不存在: {d}")

# ==== 3. 数据增强与加载 ====
train_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(15),
    transforms.ColorJitter(brightness=0.2, contrast=0.2),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                        std=[0.229, 0.224, 0.225])
])
val_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                        std=[0.229, 0.224, 0.225])
])

# ==== 4. 加载数据 ====
train_dataset = ImageFolder(train_dir, transform=train_transform)
val_dataset   = ImageFolder(val_dir,   transform=val_transform)

print("ImageFolder自动识别的训练样本数:", len(train_dataset))
print("ImageFolder自动识别的验证样本数:", len(val_dataset))
print("类别标签:", train_dataset.classes)

train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True,  num_workers=0)
val_loader   = DataLoader(val_dataset,   batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

# ==== 5. 定义模型 ====
model = models.resnet50(pretrained=True)
for param in model.parameters():
    param.requires_grad = False
model.fc = nn.Linear(model.fc.in_features, len(train_dataset.classes))
model = model.to(DEVICE)

criterion = nn.CrossEntropyLoss()
optimizer = Adam(model.fc.parameters(), lr=LEARNING_RATE)

# ==== 6. 训练 ====
for epoch in range(NUM_EPOCHS):
    print(f"\nEpoch {epoch+1}/{NUM_EPOCHS}")
    model.train()
    train_loss, train_correct, train_total = 0, 0, 0
    for images, labels in train_loader:
        images, labels = images.to(DEVICE), labels.to(DEVICE)
        outputs = model(images)
        loss = criterion(outputs, labels)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        train_loss += loss.item() * images.size(0)
        _, predicted = torch.max(outputs, 1)
        train_total += labels.size(0)
        train_correct += (predicted == labels).sum().item()
    train_acc = train_correct / train_total * 100
    train_loss = train_loss / train_total
    print(f"训练集  损失: {train_loss:.4f}，准确率: {train_acc:.2f}%")
    model.eval()
    val_loss, val_correct, val_total = 0, 0, 0
    with torch.no_grad():
        for images, labels in val_loader:
            images, labels = images.to(DEVICE), labels.to(DEVICE)
            outputs = model(images)
            loss = criterion(outputs, labels)
            val_loss += loss.item() * images.size(0)
            _, predicted = torch.max(outputs, 1)
            val_total += labels.size(0)
            val_correct += (predicted == labels).sum().item()
    val_acc = val_correct / val_total * 100
    val_loss = val_loss / val_total
    print(f"验证集  损失: {val_loss:.4f}，准确率: {val_acc:.2f}%")

# ==== 7. 保存模型 ====
model_path = "finetuned_fake_real_resnet50.pth"
torch.save(model.state_dict(), model_path)
print(f"\n✅ 微调完成，模型已保存到: {model_path}")

# ==== 8. 单图推理示例 ====
test_img_dir = r"data\val\FAKE"
imgs = [f for f in os.listdir(test_img_dir) if f.lower().endswith(('.jpg','.jpeg','.png'))]
if imgs:
    img = Image.open(os.path.join(test_img_dir, imgs[0])).convert('RGB')
    img_tensor = val_transform(img).unsqueeze(0).to(DEVICE)
    model.eval()
    with torch.no_grad():
        output = model(img_tensor)
        prob = torch.softmax(output, dim=1)[0]
        pred = torch.argmax(prob).item()
    print(f"\n测试图片: {imgs[0]}")
    print(f"预测类别: {train_dataset.classes[pred]}，置信度: {prob[pred]*100:.2f}%")
else:
    print("【警告】没有找到data\\val\\FAKE下的图片，未进行推理")
