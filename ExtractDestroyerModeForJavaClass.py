import zipfile
import os
import io
import re


"""处理毁灭者模式的 哈哈 挺艰难的"""
def find_all_offsets(data, signature):
    offsets = []
    i = 0
    while i < len(data):
        i = data.find(signature, i)
        if i == -1:
            break
        offsets.append(i)
        i += 1
    return offsets


def is_valid_class_file(class_data):
    """验证是否为有效的Java class文件"""
    return len(class_data) >= 4 and class_data[:4] == b'\xca\xfe\xba\xbe'


def scan_zip_content(zf, prefix=""):
    """递归扫描ZIP文件内容，处理嵌套ZIP"""
    results = []
    for entry in zf.namelist():
        print(f"    [检查] {prefix}{entry}")

        # 检查是否为嵌套ZIP
        if entry.lower().endswith(('.zip', '.jar', '.war', '.ear', '.apk')):
            try:
                with zf.open(entry) as nested_file:
                    nested_data = nested_file.read()
                    with zipfile.ZipFile(io.BytesIO(nested_data)) as nested_zf:
                        nested_prefix = f"{prefix}{entry}!"
                        results.extend(scan_zip_content(nested_zf, nested_prefix))
            except Exception as e:
                print(f"    ! 嵌套ZIP处理失败: {prefix}{entry} ({str(e)})")
                continue

        # 尝试读取并验证文件内容
        try:
            class_data = zf.read(entry)
            if is_valid_class_file(class_data):
                # 特殊处理：如果文件名没有扩展名，添加.class
                if not os.path.splitext(entry)[1]:
                    entry += ".class"
                results.append((f"{prefix}{entry}", class_data))
                print(f"    + 找到有效class: {prefix}{entry} (大小: {len(class_data)} 字节)")
        except Exception as e:
            print(f"    - 无法读取为class: {prefix}{entry} ({str(e)})")
            continue

    return results


def get_unique_filename(file_path, existing_files):
    """生成唯一文件名"""
    base, ext = os.path.splitext(file_path)
    counter = 1

    while file_path in existing_files:
        file_path = f"{base}_{counter}{ext}"
        counter += 1

    existing_files.add(file_path)
    return file_path


def save_class_file(class_path, class_data, output_dir="extracted_classes", existing_files=None):
    """将class文件保存到本地文件系统，确保文件名唯一"""
    if existing_files is None:
        existing_files = set()

    # 替换非法文件路径字符
    safe_path = re.sub(r'[<>:"/\\|?*]', '_', class_path)

    # 获取唯一文件名
    unique_path = get_unique_filename(safe_path, existing_files)

    # 创建保存目录
    full_path = os.path.join(output_dir, unique_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    try:
        with open(full_path, 'wb') as f:
            f.write(class_data)
        print(f"    * 成功保存: {full_path}")
        return full_path
    except Exception as e:
        print(f"    ! 保存失败: {class_path} ({str(e)})")
        return None


def scan_zip_segments(file_path):
    with open(file_path, "rb") as f:
        data = f.read()

    zip_magic = b'\x50\x4B\x03\x04'
    offsets = find_all_offsets(data, zip_magic)
    print(f"共发现 {len(offsets)} 个 ZIP 段，正在分析...\n")

    all_valid_classes = []
    output_dir = "extracted_classes"
    os.makedirs(output_dir, exist_ok=True)
    existing_files = set()  # 跟踪已保存的文件名

    for idx, offset in enumerate(offsets):
        segment = data[offset:]
        print(f"[ZIP 段 {idx} @ 偏移 {offset}]")

        try:
            with zipfile.ZipFile(io.BytesIO(segment)) as z:
                valid_classes = scan_zip_content(z)

                if not valid_classes:
                    print("  - 未找到有效 .class 文件")
                    continue

                print(f"  + 找到 {len(valid_classes)} 个有效 .class 文件")
                for cls_path, cls_data in valid_classes:
                    saved_path = save_class_file(cls_path, cls_data, output_dir, existing_files)
                    if saved_path:
                        all_valid_classes.append((cls_path, saved_path))

        except Exception as e:
            print(f"[跳过] 段 {idx} @ {offset} 无法解析为ZIP ({str(e)})")
        print()

    if not all_valid_classes:
        print("警告: 整个文件中未找到有效 .class 文件！")
    else:
        print(f"扫描完成，共找到并保存 {len(all_valid_classes)} 个有效 .class 文件:")
        for original, saved in all_valid_classes:
            print(f"  - {original} -> {saved}")


# 示例使用
scan_zip_segments("欢迎大牛破解本地验证-梦幻混淆.jar")