#!/usr/bin/env python3
"""
Test script for Telegram Collectible Gifts Parser
This script tests the Windows-adapted version of the parser
"""

import os
import sys
import json
import time
import asyncio
import subprocess
from pathlib import Path
import unittest

class TelegramGiftsParserTest(unittest.TestCase):
    """Test suite for Telegram Gifts Parser"""
    
    def setUp(self):
        """Setup test environment"""
        self.parser_dir = Path("/app/parser")
        self.output_dir = Path("/app/output")
        self.collections_dir = self.output_dir / "collections"
        self.logs_dir = self.output_dir / "logs"
        
        # Change to parser directory
        os.chdir(self.parser_dir)
        
        # Clean up any previous test results
        demo_results = self.output_dir / "demo_results.json"
        if demo_results.exists():
            os.remove(demo_results)
            
        lightsword_demo = self.collections_dir / "lightsword_demo.json"
        if lightsword_demo.exists():
            os.remove(lightsword_demo)
            
        lightsword_demo_backup = self.collections_dir / "lightsword_demo.json.backup"
        if lightsword_demo_backup.exists():
            os.remove(lightsword_demo_backup)
    
    def run_command(self, cmd):
        """Run a command and return the result"""
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                encoding='utf-8'
            )
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return 1, "", str(e)
    
    def test_1_launcher_setup(self):
        """Test the launcher setup command"""
        print("\n🔍 Testing launcher setup...")
        
        # Run the setup command
        returncode, stdout, stderr = self.run_command(
            [sys.executable, "launcher.py", "setup"]
        )
        
        # Check if the command was successful
        self.assertEqual(returncode, 0, f"Setup failed with error: {stderr}")
        self.assertIn("✅ Директории созданы", stdout, "Directory creation failed")
        self.assertIn("✅ Зависимости установлены успешно", stdout, "Dependencies installation failed")
        self.assertIn("✅ Проверка окружения прошла успешно", stdout, "Environment check failed")
        
        print("✅ Launcher setup test passed")
    
    def test_2_health_check(self):
        """Test the health check command"""
        print("\n🔍 Testing health check...")
        
        # Run the health check command
        returncode, stdout, stderr = self.run_command(
            [sys.executable, "launcher.py", "health-check"]
        )
        
        # Check if the command was successful
        self.assertEqual(returncode, 0, f"Health check failed with error: {stderr}")
        self.assertIn("✓ Configuration loaded", stdout, "Configuration check failed")
        self.assertIn("✓ File list accessible", stdout, "File list check failed")
        self.assertIn("✓ Collection files accessible", stdout, "Collection files check failed")
        self.assertIn("✓ Network connectivity OK", stdout, "Network connectivity check failed")
        self.assertIn("✓ Gift parser working", stdout, "Gift parser check failed")
        self.assertIn("🎉 All health checks passed", stdout, "Not all health checks passed")
        
        print("✅ Health check test passed")
    
    def test_3_demo_mode(self):
        """Test the demo mode"""
        print("\n🔍 Testing demo mode...")
        
        # Run the demo command
        returncode, stdout, stderr = self.run_command(
            [sys.executable, "launcher.py", "demo"]
        )
        
        # Check if the command was successful
        self.assertEqual(returncode, 0, f"Demo mode failed with error: {stderr}")
        self.assertIn("🎭 Starting demonstration parsing", stdout, "Demo parsing didn't start")
        self.assertIn("🎉 Demo parsing completed", stdout, "Demo parsing didn't complete")
        
        # Check if demo results file was created
        demo_results_file = self.output_dir / "demo_results.json"
        self.assertTrue(demo_results_file.exists(), "Demo results file was not created")
        
        # Check if the demo results file contains valid JSON
        try:
            with open(demo_results_file, 'r', encoding='utf-8') as f:
                demo_data = json.load(f)
            
            # Validate demo data structure
            self.assertIn("demo_info", demo_data, "Demo info missing in results")
            self.assertIn("sample_gifts", demo_data, "Sample gifts missing in results")
            self.assertTrue(len(demo_data["sample_gifts"]) > 0, "No sample gifts in results")
            
            # Check collection stats
            stats = demo_data["demo_info"]["stats"]
            self.assertEqual(stats["collection_name"], "lightsword_demo", "Wrong collection name")
            self.assertTrue(stats["total_urls"] > 0, "No URLs processed")
            self.assertTrue(stats["successful_parses"] > 0, "No successful parses")
            
            print(f"📊 Demo stats: {stats['successful_parses']}/{stats['total_urls']} URLs parsed successfully")
            
        except json.JSONDecodeError:
            self.fail("Demo results file contains invalid JSON")
        
        # Check if collection file was created
        collection_file = self.collections_dir / "lightsword_demo.json"
        self.assertTrue(collection_file.exists(), "Collection file was not created")
        
        # Check if backup file was created
        backup_file = self.collections_dir / "lightsword_demo.json.backup"
        self.assertTrue(backup_file.exists(), "Backup file was not created")
        
        print("✅ Demo mode test passed")
    
    def test_4_single_collection(self):
        """Test processing a single collection"""
        print("\n🔍 Testing single collection processing...")
        
        # Use a small collection for testing
        test_collection = "durovscap"  # This is one of the smaller collections
        
        # Run the collection command
        returncode, stdout, stderr = self.run_command(
            [sys.executable, "launcher.py", "collection", test_collection]
        )
        
        # Check if the command was successful
        self.assertEqual(returncode, 0, f"Collection processing failed with error: {stderr}")
        self.assertIn(f"Processing single collection: {test_collection}", stdout, "Collection processing didn't start")
        
        # Wait for the collection file to be created (it's saved every minute)
        collection_file = self.collections_dir / f"{test_collection}.json"
        backup_file = self.collections_dir / f"{test_collection}.json.backup"
        
        # Check if collection file was created
        self.assertTrue(collection_file.exists(), f"Collection file for {test_collection} was not created")
        
        # Check if backup file was created
        self.assertTrue(backup_file.exists(), f"Backup file for {test_collection} was not created")
        
        # Check if the collection file contains valid JSON
        try:
            with open(collection_file, 'r', encoding='utf-8') as f:
                collection_data = json.load(f)
            
            # Validate collection data structure
            self.assertIn("collection_name", collection_data, "Collection name missing")
            self.assertIn("gifts", collection_data, "Gifts data missing")
            self.assertTrue(len(collection_data["gifts"]) > 0, "No gifts in collection data")
            
            # Check collection info
            self.assertEqual(collection_data["collection_name"], test_collection, "Wrong collection name")
            self.assertTrue(collection_data["total_gifts"] > 0, "No gifts in collection info")
            
            print(f"📊 Collection stats: {len(collection_data['gifts'])}/{collection_data['total_gifts']} gifts parsed")
            
        except json.JSONDecodeError:
            self.fail(f"Collection file for {test_collection} contains invalid JSON")
        
        print(f"✅ Single collection ({test_collection}) test passed")
    
    def test_5_error_handling(self):
        """Test error handling with invalid collection"""
        print("\n🔍 Testing error handling with invalid collection...")
        
        # Try to process a non-existent collection
        invalid_collection = "nonexistent_collection"
        
        # Run the collection command with invalid collection
        returncode, stdout, stderr = self.run_command(
            [sys.executable, "launcher.py", "collection", invalid_collection]
        )
        
        # Check if the command failed as expected
        self.assertNotEqual(returncode, 0, "Command should fail with invalid collection")
        self.assertIn("Failed to process collection", stdout + stderr, "Error message missing")
        
        print("✅ Error handling test passed")

def run_tests():
    """Run all tests"""
    # Create test suite
    test_suite = unittest.TestSuite()
    test_suite.addTest(TelegramGiftsParserTest('test_1_launcher_setup'))
    test_suite.addTest(TelegramGiftsParserTest('test_2_health_check'))
    test_suite.addTest(TelegramGiftsParserTest('test_3_demo_mode'))
    test_suite.addTest(TelegramGiftsParserTest('test_4_single_collection'))
    test_suite.addTest(TelegramGiftsParserTest('test_5_error_handling'))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Return success or failure
    return result.wasSuccessful()

if __name__ == "__main__":
    print("🧪 Starting Telegram Gifts Parser Tests")
    print("======================================")
    
    success = run_tests()
    
    if success:
        print("\n🎉 All tests passed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)