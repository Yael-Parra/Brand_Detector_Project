from ultralytics import YOLO

model = YOLO('best1.pt')

#source = "https://omes-va.com/wp-content/uploads/2025/02/Datasets_720x405.jpg"
source = "data/troca.jpg"

result = model(source)

print(result)


print("-----")
print(result)
for box in result:
    box.show()


