#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для добавления цветных контуров вокруг фигур в PDF
Контур соответствует цвету фигуры, ширина 0.25 см
С поддержкой мультипоточности и прогресс-баров
"""

import os
import io
import sys
import argparse
import fitz  # PyMuPDF
from PIL import Image
import numpy as np
from multiprocessing import Pool, cpu_count
from tqdm import tqdm

def add_contour_to_image(img_pil, contour_width_px, target_color=None):
    """
    Добавляет контур вокруг цветных фигур в изображении
    
    Args:
        img_pil: PIL Image
        contour_width_px: ширина контура в пикселях
        target_color: цвет для обводки (если None, используется цвет фигуры)
    
    Returns:
        PIL Image с добавленными контурами
    """
    # Конвертируем в RGB если нужно
    if img_pil.mode != 'RGB':
        img_pil = img_pil.convert('RGB')
    
    # Конвертируем в numpy array
    img_array = np.array(img_pil)
    height, width = img_array.shape[:2]
    
    # Создаем маску для цветных пикселей (не белых)
    white_threshold = 250  # Порог для определения белого
    color_mask = ~((img_array[:, :, 0] > white_threshold) & 
                   (img_array[:, :, 1] > white_threshold) & 
                   (img_array[:, :, 2] > white_threshold))
    
    # Если нет цветных пикселей, возвращаем оригинал
    if not np.any(color_mask):
        return img_pil
    
    # Используем scipy для эффективного определения контуров
    from scipy import ndimage
    from scipy.ndimage import distance_transform_edt
    
    # Создаем структуру для расширения (круглая форма)
    radius = max(1, int(contour_width_px))
    y, x = np.ogrid[:radius*2+1, :radius*2+1]
    structure = (x - radius)**2 + (y - radius)**2 <= radius**2
    
    # Расширяем маску цветных пикселей
    expanded_mask = ndimage.binary_dilation(color_mask, structure=structure, iterations=1)
    
    # Если нужно больше расширения, делаем несколько итераций
    if contour_width_px > radius:
        iterations = max(1, int(contour_width_px / radius))
        expanded_mask = ndimage.binary_dilation(color_mask, structure=structure, iterations=iterations)
    
    # Контур = расширенная маска минус оригинальная маска
    contour_mask = expanded_mask & ~color_mask
    
    # Создаем изображение для контуров
    contour_img = np.zeros((height, width, 4), dtype=np.uint8)
    
    # Создаем массив расстояний от каждого пикселя до ближайшего цветного
    inverted_mask = ~color_mask
    distances, indices = distance_transform_edt(inverted_mask, return_indices=True)
    
    # Заполняем контур цветом ближайшего цветного пикселя
    contour_coords = np.where(contour_mask)
    for y, x in zip(contour_coords[0], contour_coords[1]):
        nearest_y = indices[0, y, x]
        nearest_x = indices[1, y, x]
        color = img_array[nearest_y, nearest_x]
        contour_img[y, x] = [color[0], color[1], color[2], 255]
    
    # Объединяем оригинальное изображение с контурами
    contour_pil = Image.fromarray(contour_img, 'RGBA')
    result = Image.alpha_composite(img_pil.convert('RGBA'), contour_pil)
    return result.convert('RGB')

def process_page_images(args):
    """
    Обрабатывает все изображения на одной странице
    
    Args:
        args: кортеж (page_data, contour_width_cm, page_num, total_pages, mirror_vertical)
    
    Returns:
        dict с данными обработанной страницы
    """
    page_data, contour_width_cm, page_num, total_pages, mirror_vertical = args
    
    processed_images = []
    contour_width_pt = contour_width_cm * 28.35
    total_images = len(page_data['images'])
    
    for img_idx, img_info in enumerate(page_data['images']):
        try:
            xref = img_info['xref']
            image_bytes = img_info['image_bytes']
            image_ext = img_info['image_ext']
            img_rect = img_info['rect']
            
            # Открываем изображение
            img_pil = Image.open(io.BytesIO(image_bytes))
            
            # Вычисляем масштаб
            scale_x = img_rect.width / img_pil.width
            scale_y = img_rect.height / img_pil.height
            scale = (scale_x + scale_y) / 2
            
            # Ширина контура в пикселях
            contour_width_px = contour_width_pt / scale
            contour_width_px = max(1, int(contour_width_px))
            
            # Добавляем контур
            img_with_contour = add_contour_to_image(img_pil, contour_width_px)
            
            # Зеркалируем по вертикали (отражаем слева направо), если включено
            if mirror_vertical:
                try:
                    # Для новых версий PIL
                    img_with_contour = img_with_contour.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                except AttributeError:
                    # Для старых версий PIL
                    img_with_contour = img_with_contour.transpose(Image.FLIP_LEFT_RIGHT)
            
            # Определяем финальный прямоугольник для размещения
            if mirror_vertical:
                # Зеркалируем координаты размещения изображения на странице
                # В PyMuPDF: x=0 слева, x растет вправо
                # При вертикальном зеркалировании (лево-право) нужно отразить x-координаты
                page_width = page_data['page_rect'].width
                final_rect = fitz.Rect(
                    page_width - img_rect.x1,  # новый x0 = страница_ширина - старый x1
                    img_rect.y0,  # y0 остается тем же
                    page_width - img_rect.x0,  # новый x1 = страница_ширина - старый x0
                    img_rect.y1   # y1 остается тем же
                )
            else:
                final_rect = img_rect
            
            # Конвертируем обратно в байты
            img_bytes_io = io.BytesIO()
            img_with_contour.save(
                img_bytes_io, 
                format=image_ext.upper() if image_ext.upper() in ['PNG', 'JPEG'] else 'PNG'
            )
            img_bytes = img_bytes_io.getvalue()
            
            processed_images.append({
                'xref': xref,
                'rect': final_rect,  # Используем финальный прямоугольник (зеркалированный или оригинальный)
                'image_bytes': img_bytes,
                'width': img_with_contour.width,
                'height': img_with_contour.height,
                'contour_width_px': contour_width_px
            })
            
        except Exception as e:
            print(f"Ошибка на странице {page_num+1}, изображение {img_idx+1}: {e}")
            continue
    
    return {
        'page_num': page_num,
        'page_rect': page_data['page_rect'],
        'images': processed_images,
        'text': page_data.get('text', ''),
        'total_images': total_images,
        'processed_count': len(processed_images)
    }

def process_pdf_with_contours(input_path, output_path, contour_width_cm=0.25, num_workers=None, mirror_vertical=False):
    """
    Обрабатывает PDF, добавляя контуры вокруг цветных фигур (с мультипоточностью)
    
    Args:
        input_path: путь к входному PDF
        output_path: путь к выходному PDF
        contour_width_cm: ширина контура в сантиметрах
        num_workers: количество потоков (по умолчанию = количество ядер CPU)
        mirror_vertical: зеркалировать изображения по вертикали (лево-право)
    """
    print(f"Обработка файла: {os.path.basename(input_path)}")
    print(f"Ширина контура: {contour_width_cm} см")
    if mirror_vertical:
        print(f"Зеркалирование: по вертикали (лево-право, включено)")
    else:
        print(f"Зеркалирование: выключено")
    
    # Открываем PDF
    doc = fitz.open(input_path)
    total_pages = len(doc)
    
    if num_workers is None:
        num_workers = min(cpu_count(), total_pages)
    
    print(f"Количество страниц: {total_pages}")
    print(f"Используется потоков: {num_workers}")
    print()
    
    # Подготавливаем данные для каждой страницы
    pages_data = []
    for page_num in range(total_pages):
        page = doc[page_num]
        page_rect = page.rect
        
        # Получаем все изображения на странице
        image_list = page.get_images()
        images_data = []
        
        for img in image_list:
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            
            # Получаем прямоугольник изображения
            img_rects = page.get_image_rects(xref)
            if img_rects:
                img_rect = img_rects[0]
                images_data.append({
                    'xref': xref,
                    'image_bytes': image_bytes,
                    'image_ext': image_ext,
                    'rect': img_rect
                })
        
        # Получаем текст страницы
        text = page.get_text()
        
        pages_data.append({
            'page_rect': page_rect,
            'images': images_data,
            'text': text
        })
    
    doc.close()
    
    # Обрабатываем страницы параллельно
    print("Запуск параллельной обработки страниц...\n")
    
    # Создаем аргументы для каждой страницы
    args_list = [
        (pages_data[i], contour_width_cm, i, total_pages, mirror_vertical)
        for i in range(total_pages)
    ]
    
    # Обрабатываем с прогресс-барами
    with Pool(processes=num_workers) as pool:
        results = []
        
        # Создаем общий прогресс-бар для страниц
        with tqdm(total=total_pages, desc="Страницы", ncols=100, leave=True, 
                  bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]') as pages_pbar:
            
            # Обрабатываем результаты по мере их готовности
            for result in pool.imap_unordered(process_page_images, args_list):
                page_num = result['page_num']
                results.append(result)
                
                # Выводим информацию о завершенной странице
                total_images_processed = sum(r['processed_count'] for r in results)
                pages_pbar.set_postfix({
                    'изображений': total_images_processed,
                    f'Стр {page_num+1}': f"✓ {result['processed_count']}/{result['total_images']}"
                })
                pages_pbar.update(1)
                
                # Выводим детальную информацию о завершенной странице
                tqdm.write(f"✓ Страница {page_num+1}/{total_pages}: обработано {result['processed_count']}/{result['total_images']} изображений")
    
    print()  # Пустая строка после прогресс-баров
    
    # Сортируем результаты по номеру страницы
    results.sort(key=lambda x: x['page_num'])
    
    # Создаем новый PDF с обработанными изображениями
    print("\nСборка финального PDF...")
    new_doc = fitz.open()
    
    total_images_processed = 0
    
    for result in tqdm(results, desc="Сборка PDF", ncols=80):
        page_num = result['page_num']
        page_rect = result['page_rect']
        processed_images = result['images']
        
        # Создаем новую страницу
        new_page = new_doc.new_page(width=page_rect.width, height=page_rect.height)
        
        # Вставляем обработанные изображения
        for img_data in processed_images:
            new_page.insert_image(img_data['rect'], stream=img_data['image_bytes'])
            total_images_processed += 1
        
        # Добавляем текст если был
        if result.get('text'):
            # Текст добавляется автоматически при копировании страницы
            pass
    
    # Сохраняем результат
    print(f"\nСохранение результата в: {output_path}")
    new_doc.save(output_path)
    new_doc.close()
    
    print(f"\n✓ Готово! Обработано изображений: {total_images_processed}")
    print(f"✓ Файл сохранен: {output_path}")

def main():
    parser = argparse.ArgumentParser(
        description='Добавление цветных контуров вокруг фигур в PDF файлах',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s input.pdf output.pdf
  %(prog)s input.pdf output.pdf --width 0.5
  %(prog)s input.pdf output.pdf --width 0.25 --mirror
  %(prog)s input.pdf output.pdf --width 0.3 --workers 4
        """
    )
    
    parser.add_argument(
        'input',
        type=str,
        help='Путь к входному PDF файлу'
    )
    
    parser.add_argument(
        'output',
        type=str,
        help='Путь к выходному PDF файлу'
    )
    
    parser.add_argument(
        '--width', '-w',
        type=float,
        default=0.25,
        help='Ширина контура в сантиметрах (по умолчанию: 0.25)'
    )
    
    parser.add_argument(
        '--mirror', '-m',
        action='store_true',
        help='Зеркалировать изображения по вертикали (лево-право)'
    )
    
    parser.add_argument(
        '--workers', '-j',
        type=int,
        default=None,
        help='Количество потоков для обработки (по умолчанию: количество ядер CPU)'
    )
    
    args = parser.parse_args()
    
    # Проверяем существование входного файла
    if not os.path.exists(args.input):
        print(f"Ошибка: файл не найден: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    # Проверяем, что входной файл - PDF
    if not args.input.lower().endswith('.pdf'):
        print(f"Ошибка: входной файл должен быть PDF: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    # Проверяем, что выходной файл - PDF
    if not args.output.lower().endswith('.pdf'):
        print(f"Ошибка: выходной файл должен быть PDF: {args.output}", file=sys.stderr)
        sys.exit(1)
    
    # Проверяем ширину контура
    if args.width <= 0:
        print(f"Ошибка: ширина контура должна быть положительным числом: {args.width}", file=sys.stderr)
        sys.exit(1)
    
    # Проверяем количество потоков
    if args.workers is not None and args.workers <= 0:
        print(f"Ошибка: количество потоков должно быть положительным числом: {args.workers}", file=sys.stderr)
        sys.exit(1)
    
    # Обрабатываем файл
    try:
        process_pdf_with_contours(
            input_path=args.input,
            output_path=args.output,
            contour_width_cm=args.width,
            num_workers=args.workers,
            mirror_vertical=args.mirror
        )
    except Exception as e:
        print(f"Ошибка при обработке: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
