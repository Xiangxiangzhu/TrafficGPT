import xml.etree.ElementTree as ET
import random
import numpy as np


def generate_trips(from_list, to_list, connectivity_matrix, num_trips, start_time, end_time):
    # 创建根元素
    routes = ET.Element("routes")

    # 检查矩阵尺寸是否正确
    if connectivity_matrix.shape != (len(from_list), len(to_list)):
        print("Error: Connectivity matrix dimensions do not match the length of from_list and to_list")
        return None

    trips_info = []

    # 生成trip信息
    for _ in range(num_trips):
        # 根据连通性矩阵选择起点和终点
        indices = [(i, j) for i in range(len(from_list)) for j in range(len(to_list)) if connectivity_matrix[i, j] > 0]
        if not indices:
            print("Error: No connected from-to pairs available")
            return None
        weights = [connectivity_matrix[i, j] for i, j in indices]
        from_index, to_index = indices[random.choices(range(len(indices)), weights=weights)[0]]

        f = from_list[from_index]
        t = to_list[to_index]

        # 随机选择出发时间
        depart_time = random.randint(start_time, end_time)

        # 保存trip信息
        trips_info.append((depart_time, f, t))

    # 按出发时间升序排序trip信息
    trips_info.sort(key=lambda x: x[0])

    # 创建trip元素并设置id
    for trip_id, (depart_time, f, t) in enumerate(trips_info):
        trip = ET.SubElement(routes, "trip")
        trip.set("id", str(trip_id))
        trip.set("depart", str(depart_time))
        trip.set("from", f)
        trip.set("to", t)

    # 将XML树格式化为字符串
    tree_str = ET.tostring(routes, encoding="utf-8").decode("utf-8")

    # 返回格式化的字符串
    return tree_str


if __name__ == "__main__":
    from_list = ["55083473#1.4.32", "29496808#0", "830650862", "833484977", "830653154#7", "219823957"]
    to_list = ["ramp1MergeTo", "55083473#2", "830653153", "833484978", "830650861#5", "185495393"]
    # to_list = ["29496808#2.341", "55083473#2", "830653153", "833484978", "830650861#5", "185495393"]
    # connectivity_matrix = np.array([
    #     [1, 20, 0, 0, 1, 1],
    #     [50, 1, 0, 0, 1, 1],
    #     [1, 1, 0, 0, 5, 1],
    #     [0, 0, 1, 0, 0, 0],
    #     [0, 0, 1, 1, 0, 0],
    #     [1, 1, 0, 0, 1, 1],
    # ])
    connectivity_matrix = np.array([
        [0, 0, 0, 0, 0, 0],
        [50, 0, 0, 0, 0, 0],
        [5, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [5, 0, 0, 0, 0, 0],
    ])
    num_trips = 2000
    start_time = 0
    end_time = 600

    xml_str = generate_trips(from_list, to_list, connectivity_matrix, num_trips, start_time, end_time)
    if xml_str:
        with open("test4_2.trips.xml", "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write(xml_str)
        print("Trips successfully written to output_trips.xml")
    else:
        print("Failed to generate trips")
