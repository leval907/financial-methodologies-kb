# Настройка подключения к S3 Beget Storage

## Общая информация

Данное руководство содержит инструкции по подключению к облачному объектному хранилищу S3 от Beget.

**Учетные данные проекта:**
- **S3 Endpoint**: https://s3.ru1.storage.beget.cloud
- **Bucket Name**: db6a1f644d97-la-ducem1
- **Access Key**: Указан в `.env`
- **Secret Key**: Указан в `.env`

## Технические ограничения

- Максимальное количество бакетов: 100 (может быть увеличено по запросу)
- Максимальный размер имени бакета: 50 символов (a-z, 0-9, -)
- Максимальное количество объектов в контейнере: не ограничено
- Максимальный размер объекта: 50 ТБ
- Максимальный размер имени объекта: 1024 символов UTF-8
- Максимальный размер данных для загрузки за один запрос: 5 ГБ
- Максимальное количество сегментов при сегментированной загрузке: 10000
- Максимальное количество HTTP-запросов к S3 API для аккаунта: 2000 запросов/сек
- Максимальное количество HTTP-запросов к бакету (GET, HEAD, OPTIONS): 2000 запросов/сек

## Клиенты для S3 Storage

### 1. AWS CLI

#### Установка
Следуйте [официальной инструкции AWS CLI](https://aws.amazon.com/cli/).

#### Настройка
```bash
aws configure
```

Укажите:
- **AWS Access Key ID**: Access Key из панели управления бакета
- **AWS Secret Access Key**: Secret Key из панели управления бакета
- Остальные параметры оставьте по умолчанию

#### Конфигурационные файлы

`.aws/credentials`:
```ini
[default]
aws_access_key_id = <your_access_key>
aws_secret_access_key = <your_secret_key>
```

`.aws/config`:
```ini
[default]
endpoint_url = https://s3.ru1.storage.beget.cloud
region = ru1
```

#### Использование
```bash
# Список файлов
aws s3 ls s3://db6a1f644d97-la-ducem1/ --endpoint-url https://s3.ru1.storage.beget.cloud

# Загрузка файла
aws s3 cp file.pdf s3://db6a1f644d97-la-ducem1/path/to/file.pdf --endpoint-url https://s3.ru1.storage.beget.cloud

# Синхронизация папки
aws s3 sync ./local-folder s3://db6a1f644d97-la-ducem1/remote-folder --endpoint-url https://s3.ru1.storage.beget.cloud
```

---

### 2. S3cmd

#### Установка
Следуйте [инструкциям в репозитории S3cmd](https://github.com/s3tools/s3cmd).

#### Настройка
```bash
s3cmd --configure
```

Параметры:
- **Access Key**: Access Key бакета
- **Secret Key**: Secret Key бакета
- **Default Region**: ru1
- **S3 Endpoint**: s3.ru1.storage.beget.cloud
- **DNS-style template**: %(bucket).s3.ru1.storage.beget.cloud

Конфигурация сохраняется в `~/.s3cfg`.

---

### 3. Cyberduck

#### Установка
Скачайте [Cyberduck](https://cyberduck.io/) для вашей ОС.

#### Подключение
1. Запустите Cyberduck
2. Нажмите **Новое подключение**
3. Выберите тип: **Amazon S3**
4. Параметры:
   - **Server**: s3.ru1.storage.beget.cloud
   - **Port**: 443
   - **Access Key ID**: Access Key
   - **Secret Access Key**: Secret Key
5. Нажмите **Подключиться**

---

### 4. Rclone

#### Установка
Скачайте с [официального сайта](https://rclone.org/downloads/).

#### Настройка
```bash
rclone config
```

Параметры:
- **Type**: S3 (выбрать Amazon S3 Compliant)
- **Provider**: Any other S3 compatible provider (34)
- **env_auth**: false (ввести вручную)
- **access_key_id**: Access Key
- **secret_access_key**: Secret Key
- **region**: ru1
- **endpoint**: https://s3.ru1.storage.beget.cloud
- **location_constraint**: (оставить пустым)
- **acl**: private

#### Использование
```bash
# Список бакетов
rclone lsd Beget:

# Список файлов в бакете
rclone ls Beget:db6a1f644d97-la-ducem1

# Копирование файла
rclone copy file.pdf Beget:db6a1f644d97-la-ducem1/path/to/

# Синхронизация
rclone sync ./local-folder Beget:db6a1f644d97-la-ducem1/remote-folder
```

---

### 5. MinIO Client (mc)

#### Установка
Скачайте с [официального сайта MinIO](https://min.io/docs/minio/linux/reference/minio-mc.html).

#### Настройка
```bash
mc alias set beget https://s3.ru1.storage.beget.cloud ACCESS_KEY SECRET_KEY
```

#### Использование
```bash
# Список бакетов
mc ls beget

# Список файлов
mc ls beget/db6a1f644d97-la-ducem1

# Копирование
mc cp file.pdf beget/db6a1f644d97-la-ducem1/path/to/

# Синхронизация
mc mirror ./local-folder beget/db6a1f644d97-la-ducem1/remote-folder
```

---

## SDK для разработчиков

### Подготовка
Для всех SDK создайте файлы конфигурации:

```bash
mkdir -p ~/.aws
```

`~/.aws/credentials`:
```ini
[default]
aws_access_key_id = <your_access_key>
aws_secret_access_key = <your_secret_key>
```

`~/.aws/config`:
```ini
[default]
endpoint_url = https://s3.ru1.storage.beget.cloud
region = ru1
```

---

### Python (boto3)

#### Установка
```bash
python3 -m venv venv
source venv/bin/activate
pip install boto3
```

#### Пример использования
```python
import boto3

s3 = boto3.client('s3')
bucket_name = 'db6a1f644d97-la-ducem1'

# Загрузка файла
s3.upload_file('local_file.pdf', bucket_name, 'remote/path/file.pdf')

# Список объектов
for obj in s3.list_objects(Bucket=bucket_name)['Contents']:
    print(obj['Key'])

# Скачивание
s3.download_file(bucket_name, 'remote/path/file.pdf', 'local_file.pdf')

# Получение объекта
response = s3.get_object(Bucket=bucket_name, Key='file.pdf')
content = response['Body'].read()
```

---

### JavaScript/Node.js (AWS SDK v3)

#### Установка
```bash
npm install @aws-sdk/client-s3
```

#### Пример использования
```javascript
import { S3Client, PutObjectCommand, GetObjectCommand } from "@aws-sdk/client-s3";

const s3Client = new S3Client({});
const bucketName = "db6a1f644d97-la-ducem1";

// Загрузка объекта
await s3Client.send(
  new PutObjectCommand({
    Bucket: bucketName,
    Key: "file.txt",
    Body: "Hello World!",
  })
);

// Получение объекта
const { Body } = await s3Client.send(
  new GetObjectCommand({
    Bucket: bucketName,
    Key: "file.txt",
  })
);

console.log(await Body.transformToString());
```

---

### PHP (AWS SDK)

#### Установка
```bash
composer require aws/aws-sdk-php
```

#### Пример использования
```php
<?php
require 'vendor/autoload.php';

use Aws\S3\S3Client;

$s3Client = new S3Client(['profile' => 'default']);
$bucket = 'db6a1f644d97-la-ducem1';

// Загрузка файла
$result = $s3Client->putObject([
    'Bucket' => $bucket,
    'Key' => 'file.txt',
    'SourceFile' => 'local_file.txt'
]);

// Список объектов
$results = $s3Client->getPaginator('ListObjects', ['Bucket' => $bucket]);
foreach ($results as $result) {
    foreach ($result['Contents'] as $object) {
        echo $object['Key'] . PHP_EOL;
    }
}
```

---

### Go (AWS SDK v2)

#### Установка
```bash
go get github.com/aws/aws-sdk-go-v2
go get github.com/aws/aws-sdk-go-v2/config
go get github.com/aws/aws-sdk-go-v2/service/s3
```

#### Пример использования
```go
package main

import (
    "context"
    "github.com/aws/aws-sdk-go-v2/aws"
    "github.com/aws/aws-sdk-go-v2/config"
    "github.com/aws/aws-sdk-go-v2/service/s3"
)

func main() {
    cfg, _ := config.LoadDefaultConfig(context.TODO())
    client := s3.NewFromConfig(cfg)
    bucket := "db6a1f644d97-la-ducem1"

    // Загрузка файла
    file, _ := os.Open("file.txt")
    defer file.Close()
    client.PutObject(context.TODO(), &s3.PutObjectInput{
        Bucket: aws.String(bucket),
        Key:    aws.String("file.txt"),
        Body:   file,
    })

    // Список объектов
    output, _ := client.ListObjectsV2(context.TODO(), &s3.ListObjectsV2Input{
        Bucket: aws.String(bucket),
    })
    for _, object := range output.Contents {
        fmt.Printf("key=%s\n", aws.ToString(object.Key))
    }
}
```

---

### .NET (AWS SDK)

#### Установка
```bash
dotnet add package AWSSDK.S3
```

#### Пример использования
```csharp
using Amazon.S3;
using Amazon.S3.Model;

const string bucketName = "db6a1f644d97-la-ducem1";
IAmazonS3 s3Client = new AmazonS3Client();

// Загрузка файла
await s3Client.UploadObjectFromFilePathAsync(
    bucketName, 
    "local_file.txt", 
    "remote/file.txt", 
    null
);

// Список объектов
var response = await s3Client.ListObjectsV2Async(new ListObjectsV2Request {
    BucketName = bucketName
});

foreach (var obj in response.S3Objects) {
    Console.WriteLine($"Key = {obj.Key}");
}
```

---

## Полезные ссылки

- [Официальная документация AWS CLI](https://docs.aws.amazon.com/cli/)
- [Boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [AWS SDK for JavaScript](https://docs.aws.amazon.com/sdk-for-javascript/)
- [AWS SDK for PHP](https://docs.aws.amazon.com/sdk-for-php/)
- [AWS SDK for Go](https://aws.github.io/aws-sdk-go-v2/)
- [AWS SDK for .NET](https://docs.aws.amazon.com/sdk-for-net/)

---

**Версия**: 1.0  
**Дата**: 2024-12-13
