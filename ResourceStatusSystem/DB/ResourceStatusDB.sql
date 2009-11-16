-- -----------------------------------------------------------
-- Resource Status database definition
-- -----------------------------------------------------------

DROP DATABASE IF EXISTS ResourceStatusDB;

CREATE DATABASE ResourceStatusDB;
--
-- Must set passwords for database user by replacing "must_be_set".
--
-- Create user DIRAC
USE mysql;
GRANT SELECT,INSERT,LOCK TABLES,UPDATE,DELETE,CREATE,DROP,ALTER ON ResourceStatusDB.* TO 'Dirac'@'localhost' IDENTIFIED BY 'must_be_set';
GRANT SELECT,INSERT,LOCK TABLES,UPDATE,DELETE,CREATE,DROP,ALTER ON ResourceStatusDB.* TO 'Dirac'@'%' IDENTIFIED BY 'must_be_set';

FLUSH PRIVILEGES;

-- -----------------------------------------------------------

USE ResourceStatusDB;

DROP TABLE IF EXISTS SiteTypes;
CREATE TABLE SiteTypes(
  SiteType VARCHAR(8) NOT NULL,
  Description BLOB,
  PRIMARY KEY(SiteType)
) Engine=InnoDB;

DROP TABLE IF EXISTS ResourceTypes;
CREATE TABLE ResourceTypes(
  ResourceType VARCHAR(8) NOT NULL,
  Description BLOB,
  PRIMARY KEY(ResourceType)
) Engine=InnoDB;

DROP TABLE IF EXISTS Status;
CREATE TABLE Status(
  Status VARCHAR(8) NOT NULL,
  Description BLOB,
  PRIMARY KEY(Status)
) Engine=InnoDB;

DROP TABLE IF EXISTS Sites;
CREATE TABLE Sites(
  SiteID INT UNSIGNED NOT NULL AUTO_INCREMENT,
  SiteName VARCHAR(32) NOT NULL,
  INDEX (SiteName),
  SiteType VARCHAR(8) NOT NULL,
  Description BLOB,
  Status VARCHAR(8) NOT NULL,
  Index(Status),
  Reason VARCHAR(255) NOT NULL DEFAULT 'Unspecified',
  DateCreated DATETIME NOT NULL,
  DateEffective DATETIME NOT NULL,
  DateEnd DATETIME,
  LastCheckTime DATETIME NOT NULL,
  OperatorCode VARCHAR(255),
  FOREIGN KEY(SiteType) REFERENCES SiteTypes(SiteType),
  FOREIGN KEY (Status) REFERENCES Status(Status),
  PRIMARY KEY(SiteID)
) Engine=InnoDB;

DROP TABLE IF EXISTS Resources;
CREATE TABLE Resources(
  ResourceID INT UNSIGNED NOT NULL AUTO_INCREMENT,
  ResourceName VARCHAR(32) NOT NULL,
  INDEX (ResourceName),
  ResourceType VARCHAR(8) NOT NULL,
  SiteName VARCHAR(32) NOT NULL,
  INDEX (SiteName),
  Status VARCHAR(8) NOT NULL,
  INDEX (Status),
  Reason VARCHAR(255) NOT NULL DEFAULT 'Unspecified',
  DateCreated DATETIME NOT NULL,
  DateEffective DATETIME NOT NULL,
  INDEX (DateEffective),
  DateEnd DATETIME,
  INDEX (DateEnd),
  OperatorCode VARCHAR(255) NOT NULL,
  LastCheckTime DATETIME NOT NULL,
  FOREIGN KEY (SiteName) REFERENCES Sites(SiteName),
  FOREIGN KEY (ResourceType) REFERENCES ResourceTypes(ResourceType),
  FOREIGN KEY (Status) REFERENCES Status(Status),
  PRIMARY KEY (ResourceID)
) Engine = InnoDB ;

DROP TABLE IF EXISTS Services;
CREATE TABLE Services(
  ServiceID INT UNSIGNED NOT NULL AUTO_INCREMENT,
  ServiceName VARCHAR(32) NOT NULL,
  INDEX (ServiceName),
  SiteName VARCHAR(32) NOT NULL,
  INDEX (SiteName),
  Description BLOB,
  ServiceType VARCHAR(32) NOT NULL,
  INDEX (ServiceType),
  Status VARCHAR(8) NOT NULL,
  Index(Status),
  Reason VARCHAR(255) NOT NULL DEFAULT 'Unspecified',
  DateCreated DATETIME NOT NULL,
  DateEffective DATETIME NOT NULL,
  DateEnd DATETIME,
  OperatorCode VARCHAR(255),
  FOREIGN KEY (SiteName) REFERENCES Sites(SiteName),
  FOREIGN KEY (Status) REFERENCES Status(Status),
  PRIMARY KEY(ServiceID)
) Engine=InnoDB;


DROP TABLE IF EXISTS SitesHistory;
CREATE TABLE SitesHistory(
  SitesHistoryID INT UNSIGNED NOT NULL AUTO_INCREMENT,
  SiteName VARCHAR(32) NOT NULL,
  Status VARCHAR(8) NOT NULL,
  Reason VARCHAR(255) NOT NULL,
  DateCreated DATETIME NOT NULL,
  DateEffective DATETIME NOT NULL,
  DateEnd DATETIME NOT NULL,
  OperatorCode VARCHAR(255),
  PRIMARY KEY(SitesHistoryID)
) Engine = InnoDB ;

DROP TABLE IF EXISTS ResourcesHistory;
CREATE TABLE ResourcesHistory(
  ResourcesHistoryID INT UNSIGNED NOT NULL AUTO_INCREMENT,
  ResourceName VARCHAR(32) NOT NULL,
  SiteName VARCHAR(32) NOT NULL,
  Status VARCHAR(8) NOT NULL,
  Reason VARCHAR(255) NOT NULL,
  DateCreated DATETIME NOT NULL,
  DateEffective DATETIME NOT NULL,
  DateEnd DATETIME NOT NULL,
  OperatorCode VARCHAR(255) NOT NULL,
  PRIMARY KEY (ResourcesHistoryID)
) Engine=InnoDB;

DROP TABLE IF EXISTS ServicesHistory;
CREATE TABLE ServicesHistory(
  ServicesHistoryID INT UNSIGNED NOT NULL AUTO_INCREMENT,
  ServiceName VARCHAR(32) NOT NULL,
  SiteName VARCHAR(32) NOT NULL,
  Status VARCHAR(8) NOT NULL,
  Reason VARCHAR(255) NOT NULL,
  DateCreated DATETIME NOT NULL,
  DateEffective DATETIME NOT NULL,
  DateEnd DATETIME,
  LastCheckTime DATETIME NOT NULL,
  OperatorCode VARCHAR(255),
  PRIMARY KEY(ServicesHistoryID)
) Engine=InnoDB;


DROP VIEW IF EXISTS PresentResources;
CREATE VIEW PresentResources AS SELECT 
  Resources.ResourceName, 
  Resources.SiteName, 
  Resources.ResourceType, 
  Resources.Status,
  Resources.DateEffective, 
  ResourcesHistory.Status AS FormerStatus,
  Resources.Reason,
  Resources.LastCheckTime,
  Resources.OperatorCode
FROM Resources INNER JOIN ResourcesHistory ON 
  Resources.ResourceName = ResourcesHistory.ResourceName AND 
  Resources.DateEffective = ResourcesHistory.DateEnd 
WHERE Resources.DateEffective < UTC_TIMESTAMP()
ORDER BY SiteName;

DROP VIEW IF EXISTS PresentSites;
CREATE VIEW PresentSites AS SELECT 
  Sites.SiteName, 
  Sites.SiteType,
  Sites.Status,
  Sites.DateEffective, 
  SitesHistory.Status AS FormerStatus,
  Sites.Reason,
  Sites.LastCheckTime,
  Sites.OperatorCode
FROM Sites INNER JOIN SitesHistory ON 
  Sites.SiteName = SitesHistory.SiteName AND 
  Sites.DateEffective = SitesHistory.DateEnd 
WHERE Sites.DateEffective < UTC_TIMESTAMP()
ORDER BY SiteName;

DROP VIEW IF EXISTS PresentServices;
CREATE VIEW PresentServices AS SELECT 
  Services.ServiceName, 
  Services.ServiceType, 
  Services.Status,
  Services.DateEffective, 
  ServicesHistory.Status AS FormerStatus,
  Services.Reason,
  Services.OperatorCode
FROM Services INNER JOIN ServicesHistory ON 
  Services.ServiceName = ServicesHistory.ServiceName AND 
  Services.DateEffective = ServicesHistory.DateEnd 
WHERE Services.DateEffective < UTC_TIMESTAMP()
ORDER BY ServiceName;