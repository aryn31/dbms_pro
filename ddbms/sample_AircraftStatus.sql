-- MySQL dump 10.13  Distrib 8.0.36, for macos14 (arm64)
--
-- Host: 127.0.0.1    Database: sample
-- ------------------------------------------------------
-- Server version	8.4.0

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `AircraftStatus`
--

DROP TABLE IF EXISTS `AircraftStatus`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `AircraftStatus` (
  `StatusID` int NOT NULL,
  `AircraftID` int DEFAULT NULL,
  `Status` varchar(50) DEFAULT NULL,
  `StatusDate` date DEFAULT NULL,
  PRIMARY KEY (`StatusID`),
  KEY `AircraftID` (`AircraftID`),
  CONSTRAINT `aircraftstatus_ibfk_1` FOREIGN KEY (`AircraftID`) REFERENCES `Aircraft` (`AircraftID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `AircraftStatus`
--

LOCK TABLES `AircraftStatus` WRITE;
/*!40000 ALTER TABLE `AircraftStatus` DISABLE KEYS */;
INSERT INTO `AircraftStatus` VALUES (1,1,'Operational','2024-11-01'),(2,2,'Under Maintenance','2024-11-10'),(3,3,'Out of Service','2024-11-12'),(4,4,'Operational','2024-11-15'),(5,5,'Scheduled for Maintenance','2024-11-18'),(6,6,'Operational','2024-11-01'),(7,7,'Under Inspection','2024-11-20'),(8,8,'Operational','2024-11-15'),(9,9,'Out of Service','2024-11-14'),(10,10,'Scheduled for Inspection','2024-11-19');
/*!40000 ALTER TABLE `AircraftStatus` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2024-12-10 19:09:51
