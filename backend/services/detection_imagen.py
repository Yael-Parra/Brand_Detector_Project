from ultralytics import YOLO

model = YOLO("best_v5.pt")

#source = "https://omes-va.com/wp-content/uploads/2025/02/Datasets_720x405.jpg"
source = "data/mrc26.jpg"

result = model(source)

print(result)


print("-----")
print(result)
for box in result:
    box.show()


