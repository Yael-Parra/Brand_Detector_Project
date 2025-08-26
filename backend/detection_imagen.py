from ultralytics import YOLO

model = YOLO('yolo11n.pt')

source = "https://omes-va.com/wp-content/uploads/2025/02/Datasets_720x405.jpg"
# source = "data/mrc26.jpg"

result = model(source)

print(result)

for result in results:
    print("-----")
    print(result)
    print(result.boxes)
    result.show()

