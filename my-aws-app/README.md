# 🚀 AWS Assignment 1 – L1
### Scalable Web App with Monitoring and Automation

---

## 📁 Project Structure

```
my-aws-app/
├── .github/
│   └── workflows/
│       └── deploy.yml          # CI/CD: GitHub Actions → Elastic Beanstalk
├── templates/
│   └── index.html              # Web UI
├── lambda/
│   └── lambda_function.py      # SQS → CloudWatch Lambda
├── app.py                      # Flask web application
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker configuration
├── Procfile                    # Tells EBS how to run the app
└── README.md
```

---

## ☁️ AWS Manual Setup (Do in Order)

### STEP 1 — VPC & Subnets
1. AWS Console → **VPC** → **Create VPC**
2. Choose **"VPC and more"**
3. Settings:
   - Name: `my-app-vpc`
   - IPv4 CIDR: `10.0.0.0/16`
   - Availability Zones: `2`
   - Public subnets: `1`
   - Private subnets: `1`
   - NAT Gateway: **None**
4. Click **Create VPC** → take screenshot

---

### STEP 2 — Elastic Beanstalk
1. **Elastic Beanstalk** → **Create Application**
2. Application name: `my-web-app`
3. Platform: **Python 3.12**
4. Code: Upload `deploy.zip` (zip all files except .git)
5. **Configure more options**:
   - Network → VPC: `my-app-vpc`
   - Subnet: **Public subnet**
   - Instance type: `t3.micro`
6. Create → take screenshot of **Green health status**

> 🔧 **Environment Variables** to set in EBS → Configuration → Software:
> ```
> RDS_HOSTNAME = <your-rds-endpoint>
> RDS_USERNAME = admin
> RDS_PASSWORD = <your-password>
> RDS_DB_NAME  = myappdb
> RDS_PORT     = 3306
> S3_BUCKET    = <your-bucket-name>
> ```

---

### STEP 3 — RDS Database
1. **RDS** → **Create database**
2. Engine: **MySQL**, Template: **Free Tier**
3. Instance class: `db.t3.micro`
4. DB name: `myappdb`, Username: `admin`
5. Connectivity:
   - VPC: `my-app-vpc`
   - Create new **subnet group** using **private subnets only**
   - Public access: **No**
6. Take screenshot → note down the **Endpoint URL**

---

### STEP 4 — Security Groups (EBS → RDS)
1. **EC2** → **Security Groups** → **Create security group**
2. Name: `rds-sg`, VPC: `my-app-vpc`
3. **Inbound rule**:
   - Type: `MySQL/Aurora`
   - Port: `3306`
   - Source: **(select the EBS security group)**
4. Attach `rds-sg` to your RDS instance
5. Take screenshot of inbound rules

---

### STEP 5 — SQS Queue
1. **SQS** → **Create queue**
2. Type: **Standard**, Name: `file-upload-queue`
3. **Access Policy** → Advanced → paste:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "s3.amazonaws.com" },
    "Action": "sqs:SendMessage",
    "Resource": "<YOUR-SQS-ARN>",
    "Condition": {
      "ArnLike": { "aws:SourceArn": "arn:aws:s3:::<YOUR-BUCKET-NAME>" }
    }
  }]
}
```
4. Create queue → **copy the ARN**
5. Take screenshot

---

### STEP 6 — S3 Bucket
1. **S3** → **Create bucket**
2. Name: `my-app-bucket-<your-name>` (must be globally unique)
3. Region: same as everything else
4. After creation → **Properties** → **Event notifications** → **Create**:
   - Name: `upload-trigger`
   - Events: `PUT`
   - Destination: **SQS** → `file-upload-queue`
5. Take screenshot of event notification

---

### STEP 7 — S3 Bucket Policy (Public Read for Static Files)
1. S3 Bucket → **Permissions** tab
2. **Block Public Access** → Edit → **uncheck all** → Save
3. **Bucket Policy** → Edit → paste:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "PublicReadStaticFiles",
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::<YOUR-BUCKET-NAME>/static/*"
  }]
}
```
4. Take screenshot

---

### STEP 8 — Lambda Function
1. **Lambda** → **Create function**
2. Name: `sqs-processor`
3. Runtime: **Python 3.12**
4. Permissions: **Create new role with basic Lambda permissions**
5. Copy-paste the code from `lambda/lambda_function.py`
6. **Add Trigger** → **SQS** → select `file-upload-queue`
7. Take screenshot of trigger config
8. **Test**: Upload a file to S3 → check CloudWatch Logs

---

### STEP 9 — CloudWatch Monitoring on EBS & RDS
**EBS:**
- EB Environment → **Monitoring** tab (already enabled by default)
- Take screenshot

**RDS:**
- RDS → Your DB → **Monitoring** tab
- Take screenshot of CPU/connection graphs

---

### STEP 10 — CloudWatch Alarms (CPU on EBS & RDS)
**For EBS:**
1. **CloudWatch** → **Alarms** → **Create alarm**
2. Metric: **EC2 → Per-Instance Metrics → CPUUtilization**
3. Select the EC2 instance inside your EB environment
4. Condition: `Greater than 70` for 1 period (5 min)
5. Action: **Create SNS topic** → enter your email → confirm
6. Name: `EBS-High-CPU-Alarm`
7. Take screenshot

**For RDS:**
1. Same steps, Metric: **RDS → Per-Database → CPUUtilization**
2. Name: `RDS-High-CPU-Alarm`
3. Take screenshot

---

### STEP 11 — CloudWatch Logs for EBS
1. **Elastic Beanstalk** → Your Environment → **Configuration**
2. **Software** → Edit → Enable **Log streaming** → Apply
3. **CloudWatch** → **Log groups** → find `/aws/elasticbeanstalk/<env>/...`
4. Take screenshot of logs

---

## 🔄 CI/CD Setup (GitHub Actions)

### Step 1: Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<your-username>/my-aws-app.git
git push -u origin main
```

### Step 2: Create AWS IAM User for CI/CD
1. **IAM** → **Users** → **Create user**
2. Name: `github-actions-user`
3. Permissions: Attach policies:
   - `AWSElasticBeanstalkFullAccess`
   - `AmazonS3FullAccess`
4. **Security credentials** → **Create access key** → copy both keys

### Step 3: Add GitHub Secrets
1. GitHub repo → **Settings** → **Secrets and variables** → **Actions**
2. Add:
   - `AWS_ACCESS_KEY_ID` = your key ID
   - `AWS_SECRET_ACCESS_KEY` = your secret key

### Step 4: Update deploy.yml
Open `.github/workflows/deploy.yml` and change:
```yaml
env:
  AWS_REGION:   us-east-1        # ← your region
  EB_APP_NAME:  my-web-app       # ← your EB app name
  EB_ENV_NAME:  my-web-app-env   # ← your EB environment name
```

### Step 5: Trigger the Pipeline
```bash
git add .
git commit -m "Trigger CI/CD"
git push
```
GitHub Actions will automatically build and deploy to Elastic Beanstalk!

---

## 📸 Screenshots Checklist

| # | Task | What to Screenshot |
|---|------|--------------------|
| 1 | VPC | VPC dashboard with subnets |
| 2 | Elastic Beanstalk | Green health status + app URL |
| 3 | RDS | DB instance in private subnet |
| 4 | Security Groups | EBS → RDS inbound rule |
| 5 | SQS Queue | Queue with message count |
| 6 | S3 + Event Notification | Event notification config |
| 7 | S3 Bucket Policy | Policy JSON applied |
| 8 | Lambda | Function with SQS trigger |
| 9 | CloudWatch Logs (Lambda) | Log entries after file upload |
| 10 | CloudWatch Monitoring EBS | CPU/memory graphs |
| 11 | CloudWatch Monitoring RDS | DB metric graphs |
| 12 | CloudWatch Alarms | Both alarms listed |
| 13 | EBS Logs in CloudWatch | Log group entries |
| 14 | CI/CD Pipeline | GitHub Actions green checkmark |

---

## ⚠️ Cost Saving Tips
- Use `t3.micro` and `db.t3.micro` (free tier)
- **Delete all resources after submission** to avoid charges
- Disable NAT Gateway (not needed for this assignment)
- Set CloudWatch alarms to notify before costs spike
