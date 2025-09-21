#!/usr/bin/env python3
"""
Complete SMS Processing Pipeline Runner
======================================

Single command to run the entire SMS processing pipeline from raw JSON to final transactions.

Usage:
    # Using existing user_id
    python3 run_complete_pipeline.py --input test_sms.json --user-id "usr_abc123"
    
    # Using phone number (finds or creates user)
    python3 run_complete_pipeline.py --input test_sms.json --phone "+91-9876543210" --name "John Doe"
    
    # Creating new user with complete info
    python3 run_complete_pipeline.py --input test_sms.json --name "Jane Smith" --email "jane@example.com" --phone "+91-9876543210"
"""

import os
import sys
import argparse
import subprocess
import json
from datetime import datetime
from typing import Dict, Any, Optional

def run_command(cmd: list, description: str, check_success: bool = True) -> Dict[str, Any]:
    """Run a command and return result with logging"""
    print(f"\n{'='*60}")
    print(f"🚀 STEP: {description}")
    print(f"{'='*60}")
    print(f"💻 Command: {' '.join(cmd)}")
    print(f"⏰ Started: {datetime.now().strftime('%H:%M:%S')}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        
        # Print output in real-time style
        if result.stdout:
            print("📤 STDOUT:")
            print(result.stdout)
        
        if result.stderr:
            print("📤 STDERR:")
            print(result.stderr)
        
        if check_success and result.returncode != 0:
            print(f"❌ FAILED: {description}")
            print(f"   Exit code: {result.returncode}")
            return {"success": False, "error": result.stderr, "exit_code": result.returncode}
        
        print(f"✅ SUCCESS: {description}")
        return {"success": True, "stdout": result.stdout, "stderr": result.stderr}
        
    except Exception as e:
        print(f"❌ EXCEPTION in {description}: {e}")
        return {"success": False, "error": str(e)}

def extract_user_id_from_output(output: str) -> Optional[str]:
    """Extract user_id from command output"""
    lines = output.split('\n')
    for line in lines:
        if 'user_id:' in line.lower() or 'user id:' in line.lower():
            # Try to extract user_id pattern
            import re
            pattern = r'usr_[a-f0-9_]+'
            match = re.search(pattern, line)
            if match:
                return match.group(0)
    return None

def main():
    parser = argparse.ArgumentParser(
        description="Run complete SMS processing pipeline from raw JSON to final transactions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using existing user_id
  python3 run_complete_pipeline.py --input test_sms.json --user-id "usr_abc123"
  
  # Using phone number (auto-finds user)
  python3 run_complete_pipeline.py --input test_sms.json --phone "+91-9876543210"
  
  # Creating new user
  python3 run_complete_pipeline.py --input test_sms.json --name "John" --phone "+91-9876543210" --email "john@example.com"
        """
    )
    
    # Input file
    parser.add_argument("--input", required=True, help="Path to SMS JSON file")
    
    # User identification (one of these required)
    user_group = parser.add_mutually_exclusive_group()
    user_group.add_argument("--user-id", help="Existing user ID")
    user_group.add_argument("--phone", help="Phone number (finds existing or creates new user)")
    
    # User creation info (optional)
    parser.add_argument("--name", help="User name (for new user creation)")
    parser.add_argument("--email", help="User email (for new user creation)")
    
    # Pipeline configuration
    parser.add_argument("--batch-size", type=int, default=5, help="Processing batch size (default: 5)")
    parser.add_argument("--model", default="qwen3:8b", help="LLM model to use (default: qwen3:8b)")
    parser.add_argument("--skip-date-conversion", action="store_true", help="Skip final date conversion step")
    parser.add_argument("--create-indexes", action="store_true", help="Create database indexes")
    
    # Debug options
    parser.add_argument("--dry-run", action="store_true", help="Show commands without executing")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Validation
    if not args.user_id and not args.phone and not args.name:
        print("❌ ERROR: Must provide either --user-id, --phone, or --name for user identification")
        return 1
    
    if not os.path.exists(args.input):
        print(f"❌ ERROR: Input file not found: {args.input}")
        return 1
    
    print("🎊 COMPLETE SMS PROCESSING PIPELINE")
    print("=" * 60)
    print(f"📁 Input file: {args.input}")
    print(f"👤 User identification: {args.user_id or args.phone or args.name}")
    print(f"📦 Batch size: {args.batch_size}")
    print(f"🤖 Model: {args.model}")
    print(f"🔧 Mode: {'DRY RUN' if args.dry_run else 'LIVE EXECUTION'}")
    print("=" * 60)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - Commands will be shown but not executed")
    
    # Track pipeline state
    pipeline_state = {
        "user_id": args.user_id,
        "steps_completed": [],
        "steps_failed": []
    }
    
    try:
        # STEP 1: User Management (if needed)
        if not args.user_id:
            print(f"\n🔍 User ID not provided, managing user creation/lookup...")
            
            user_cmd = ["python3", "user_manager.py"]
            
            if args.phone:
                # Try to find existing user by phone
                user_cmd.extend(["--find-phone", args.phone])
                if args.name:
                    user_cmd.extend(["--name", args.name])
                if args.email:
                    user_cmd.extend(["--email", args.email])
            else:
                # Create new user
                user_cmd.extend(["--create"])
                if args.name:
                    user_cmd.extend(["--name", args.name])
                if args.email:
                    user_cmd.extend(["--email", args.email])
                if args.phone:
                    user_cmd.extend(["--phone", args.phone])
            
            if args.dry_run:
                print(f"📋 WOULD RUN: {' '.join(user_cmd)}")
            else:
                user_result = run_command(user_cmd, "User Management")
                if not user_result["success"]:
                    print("❌ PIPELINE FAILED at User Management step")
                    return 1
                
                # Extract user_id from output
                extracted_user_id = extract_user_id_from_output(user_result["stdout"])
                if extracted_user_id:
                    pipeline_state["user_id"] = extracted_user_id
                    print(f"✅ Extracted user_id: {extracted_user_id}")
                else:
                    print("⚠️  Could not extract user_id from output, proceeding with manual input...")
            
            pipeline_state["steps_completed"].append("user_management")
        
        # STEP 2: SMS Data Upload
        upload_cmd = [
            "python3", "sms_mongodb_uploader.py",
            "--input", args.input
        ]
        
        if pipeline_state["user_id"]:
            upload_cmd.extend(["--user-id", pipeline_state["user_id"]])
        else:
            # Use phone and name for upload
            if args.phone:
                upload_cmd.extend(["--user-phone", args.phone])
            if args.name:
                upload_cmd.extend(["--user-name", args.name])
            if args.email:
                upload_cmd.extend(["--user-email", args.email])
        
        if args.create_indexes:
            upload_cmd.append("--create-indexes")
        
        upload_cmd.append("--stats")
        
        if args.dry_run:
            print(f"📋 WOULD RUN: {' '.join(upload_cmd)}")
        else:
            upload_result = run_command(upload_cmd, "SMS Data Upload")
            if not upload_result["success"]:
                print("❌ PIPELINE FAILED at SMS Upload step")
                return 1
            
            # Extract user_id if still not found
            if not pipeline_state["user_id"]:
                extracted_user_id = extract_user_id_from_output(upload_result["stdout"])
                if extracted_user_id:
                    pipeline_state["user_id"] = extracted_user_id
        
        pipeline_state["steps_completed"].append("sms_upload")
        
        # STEP 3: MongoDB Pipeline Processing
        if not pipeline_state["user_id"]:
            print("⚠️  No user_id determined yet - will let pipeline handle user identification")
            # In dry run mode or when phone is used, we may not have user_id yet
            if args.dry_run:
                print("🔍 In dry run mode, assuming pipeline will handle user identification")
        
        pipeline_cmd = [
            "python3", "mongodb_pipeline.py",
            "--batch-size", str(args.batch_size),
            "--model", args.model
        ]
        
        # Add user_id if available
        if pipeline_state["user_id"]:
            pipeline_cmd.extend(["--user-id", pipeline_state["user_id"]])
        elif args.dry_run:
            pipeline_cmd.extend(["--user-id", "PLACEHOLDER_USER_ID"])
        
        if args.dry_run:
            print(f"📋 WOULD RUN: {' '.join(pipeline_cmd)}")
        else:
            pipeline_result = run_command(pipeline_cmd, "MongoDB Pipeline Processing")
            if not pipeline_result["success"]:
                print("❌ PIPELINE FAILED at MongoDB Pipeline step")
                return 1
        
        pipeline_state["steps_completed"].append("mongodb_pipeline")
        
        # STEP 4: Date Conversion (optional)
        if not args.skip_date_conversion:
            conversion_cmd = [
                "python3", "convert_transaction_dates.py",
                "--db", "pluto_money",
                "--source", "financial_transactions",
                "--dest", "user_financial_transactions",
                "--force"  # 🚀 NEW: Auto-proceed without confirmation for automation
            ]
            
            # 🚀 NEW: Add user-specific filtering if user_id is available
            if pipeline_state["user_id"]:
                conversion_cmd.extend(["--user-id", pipeline_state["user_id"]])
                print(f"   🎯 Will process only user: {pipeline_state['user_id']}")
            else:
                print(f"   🌐 Will process ALL users in financial_transactions")
            
            if args.dry_run:
                print(f"📋 WOULD RUN: {' '.join(conversion_cmd)}")
            else:
                conversion_result = run_command(conversion_cmd, "Date Conversion", check_success=False)
                # Date conversion might ask for user input, so we don't fail the pipeline
                if conversion_result["success"]:
                    pipeline_state["steps_completed"].append("date_conversion")
                else:
                    print("⚠️  Date conversion had issues, but pipeline continues...")
                    pipeline_state["steps_failed"].append("date_conversion")
        else:
            print("⏭️  Skipping date conversion step as requested")
        
        # FINAL SUCCESS
        print(f"\n{'='*60}")
        print("🎉 COMPLETE PIPELINE EXECUTION SUCCESSFUL!")
        print(f"{'='*60}")
        print(f"✅ User ID: {pipeline_state['user_id']}")
        print(f"✅ Steps completed: {', '.join(pipeline_state['steps_completed'])}")
        if pipeline_state['steps_failed']:
            print(f"⚠️  Steps with issues: {', '.join(pipeline_state['steps_failed'])}")
        print(f"📊 Input file: {args.input}")
        print(f"💾 Final data location: pluto_money.user_financial_transactions")
        print("=" * 60)
        
        return 0
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Pipeline interrupted by user")
        return 130
    except Exception as e:
        print(f"\n❌ PIPELINE FAILED with unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
