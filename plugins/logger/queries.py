#!/usr/bin/env python3

DDL = '''
CREATE TABLE IF NOT EXISTS `{schema}`.`{log_table}` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `author` VARCHAR(255) NOT NULL,
    `level` VARCHAR(255) NOT NULL,
    `message` VARCHAR(255) NOT NULL,
    `timestamp` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
PRIMARY KEY (`id`))
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8;
'''
# schema , log_table

def LOG_ROW(author, level, message):
    return '("{author}","{level}","{message}")'.format(
        author=author,
        level=level,
        message=message
    )

def INSERT_LOGS(schema, log_table, rows):
    return'''
        INSERT INTO `{schema}`.`{log_table}`
        (author, level, message)
        VALUES
        {rows}
    '''.format(
        schema=schema,
        log_table=log_table,
        rows=','.join([rows]),
    )