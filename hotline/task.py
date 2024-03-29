# Author: Jorge Alarcon Alvarez
# Email: jorge4larcon@gmail.com
"""This module defines tasks (threads) of the application."""

from PyQt5 import QtCore
import inbox
import asyncio
import ftplib
import os
import inter
import logging
import configuration


# def recvall(sock: socket.socket, length):
#     data = b''
#     while len(data) < length:
#         more = sock.recv(length - len(data))
#         if not more:
#             raise EOFError()

class GetContactInformationForChatSignals(QtCore.QObject):
    """This class defines the signals of a GetContactInformationForChatThread"""
    # remote_name
    on_error = QtCore.pyqtSignal(str, 'PyQt_PyObject')
    # remote_mac, local_mac, remote_name, message, contact_info
    on_result = QtCore.pyqtSignal(str, str, str, str, dict)
    on_finished = QtCore.pyqtSignal()


class GetContactInformationForChatThread(QtCore.QRunnable):
    """This class defines the GetContactInformationForChatThread thread"""
    def __init__(self, remote_ip, remote_port, remote_name, remote_mac, message, local_mac):
        super(GetContactInformationForChatThread, self).__init__()
        self.remote_ip = remote_ip
        self.remote_port = remote_port
        self.remote_name = remote_name
        self.remote_mac = remote_mac
        self.local_mac = local_mac
        self.message = message
        self.signals = GetContactInformationForChatSignals()

    def run(self) -> None:
        """This method obtains contact information to start a chat"""
        try:
            result = asyncio.run(inbox.get_contact_information(self.remote_ip, self.remote_ip))
        except Exception as e:
            self.signals.on_error.emit(self.remote_name, e)
        else:
            self.signals.on_result.emit(self.remote_mac, self.local_mac, self.remote_name, self.message, result)
        finally:
            self.signals.on_finished.emit()


class RequestContactInformationSignals(QtCore.QObject):
    """These are the signals emitted by the RequestContactInformationThread"""
    on_fail = QtCore.pyqtSignal(str, str)
    on_success = QtCore.pyqtSignal(dict)


class RequestContactInformationThread(QtCore.QRunnable):
    """This thread requests contact information to another contact"""
    def __init__(self, ip4, ip6, mac, name, port, inter_server_ip, inter_server_port, inter_server_password,
                 timeout=3):
        super(RequestContactInformationThread, self).__init__()
        self.ip6 = ip6
        self.ip4 = ip4
        self.port = port
        self.name = name
        self.mac = mac
        self.ip6lleui64 = configuration.generate_ipv6_linklocal_eui64_address(self.mac)
        self.timeout = timeout
        self.inter_server_ip = inter_server_ip
        self.inter_server_port = inter_server_port
        self.inter_server_password = inter_server_password

        self.signals = RequestContactInformationSignals()

    def run(self) -> None:
        """This is the method that is called when the thread starts"""
        logging.info(f"Requesting information to {self.name} {self.mac}")
        if self.ip4 and self.ip6:
            self.ir_ip4_ip6()
        elif self.ip4 and not self.ip6:
            self.ir_ip4_noip6()
        elif not self.ip4 and self.ip6:
            self.ir_noip4_ip6()
        elif not self.ip4 and not self.ip6:
            self.ir_noip4_noip6()

    def ir_ip4_ip6(self):
        """This function is called to request contact information"""
        logging.info(f"{self.name} has IPv4 and IPv6 address")
        try:
            logging.info(f"Requesting information to {self.name} using {self.ip4}")
            ci = asyncio.run(inbox.get_contact_information(self.ip4, self.port, self.timeout))
        except Exception as e:
            logging.info(f'Information request failed')
            self.ir_noip4_ip6()
        else:
            if ci['mac_address'] == self.mac:
                logging.info('Information request succeeded')
                self.signals.on_success.emit(ci)
            else:
                logging.info(f'Unexpected user replied to the information request')
                self.ir_noip4_ip6()

    def ir_noip4_ip6(self):
        """This function is called to request contact information"""
        logging.info(f"{self.name} has IPv6 address")
        try:
            logging.info(f"Requesting information to {self.name} using {self.ip6}")
            ci = asyncio.run(inbox.get_contact_information(self.ip6, self.port, self.timeout))
        except Exception as e:
            logging.info('Information request failed, generating IPv6 Link Local EUI-64 address')
            if self.ip6lleui64 == self.ip6:
                logging.info('The IPv6 Link Local EUI-64 address is the same as the IPv6 address used')
                if self.inter_server_ip:
                    logging.info('Interlocutor address provided, requesting contact information to the server')
                    self.ir_interlocutor()
                else:
                    logging.info('Could not obtain the contact information')
                    self.signals.on_fail.emit(self.name, self.mac)
            else:
                logging.info('Trying to request information using IPv6 Link Local EUI-64 address')
                self.ir_noip4_noip6()
        else:
            if ci['mac_address'] == self.mac:
                logging.info('Information request succeeded')
                self.signals.on_success.emit(ci)
            else:
                logging.info(f'Unexpected user replied to the information request')
                self.ir_noip4_noip6()

    def ir_ip4_noip6(self):
        """This function is called to request contact information"""
        logging.info(f"{self.name} has IPv4 address")
        try:
            logging.info(f"Requesting information to {self.name} using {self.ip4}")
            ci = asyncio.run(inbox.get_contact_information(self.ip4, self.port, self.timeout))
        except Exception as e:
            logging.info('Information request failed')
            self.ir_noip4_noip6()
        else:
            if ci['mac_address'] == self.mac:
                logging.info('Information request succeeded')
                self.signals.on_success.emit(ci)
            else:
                logging.info(f'Unexpected user replied to the information request')
                self.ir_noip4_noip6()

    def ir_noip4_noip6(self):
        """This function is called to request contact information"""
        try:
            logging.info(f"Requesting contact information using IPv6 Link Local EUI-64 address...")
            ci = asyncio.run(inbox.get_contact_information(self.ip6lleui64, self.port, self.timeout))
        except Exception as e:
            logging.info('Information request failed')
            if self.inter_server_ip:
                logging.info('Interlocutor address provided, requesting contact information to the server')
                self.ir_interlocutor()
            else:
                logging.info('Could not obtain the contact information')
                self.signals.on_fail.emit(self.name, self.mac)
        else:
            if ci['mac_address'] == self.mac:
                logging.info('Information request succeeded')
                self.signals.on_success.emit(ci)
            else:
                logging.info(f'Unexpected user replied to the information request')
                if self.inter_server_ip:
                    logging.info('Interlocutor address provided, requesting contact information to the server')
                    self.ir_interlocutor()
                else:
                    logging.info('Could not obtain the contact information')
                    self.signals.on_fail.emit(self.name, self.mac)

    def ir_interlocutor(self):
        """This function is called to request contact information"""
        try:
            logging.info(f"Sending a 'GET by MAC' request to the Interlocutor server {self.inter_server_ip}:{self.inter_server_port}")
            req = inter.get_by_mac(self.mac)
            ci = asyncio.run(
                req.send_to(self.inter_server_ip, self.inter_server_port, timeout=self.timeout,
                            password=self.inter_server_password))
        except Exception as e:
            logging.info('Could not obtain the contact information')
            self.signals.on_fail.emit(self.name, self.mac)
        else:
            logging.info(f"'GET by MAC' request succeeded")
            ci = ci.get('client')
            if ci:
                try:
                    ip4 = ci['ipv4_addr']
                    port = ci['port']
                    logging.info(f'Interlocutor suggested the address: {ip4}:{port}')
                except Exception as e:
                    logging.info('Could not obtain the contact information')
                    self.signals.on_fail.emit(self.name, self.mac)
                else:
                    if ip4 == self.ip4 and port == self.port:
                        logging.info('The Interlocutor suggested an address that was tested, but did not work')
                        logging.info('Could not obtain the contact information')
                        self.signals.on_fail.emit(self.name, self.mac)
                    else:
                        try:
                            logging.info('Requesting contact information with the address provided')
                            ci = asyncio.run(inbox.get_contact_information(ip4, port, self.timeout))
                        except Exception as e:
                            logging.info('Could not obtain the contact information')
                            self.signals.on_fail.emit(self.name, self.mac)
                        else:
                            if ci['mac_address'] == self.mac:
                                logging.info('Information request succeeded')
                                self.signals.on_success.emit(ci)
                            else:
                                logging.info('Could not obtain the contact information')
                                self.signals.on_fail.emit(self.name, self.mac)
            else:
                logging.info('Could not obtain the contact information')
                self.signals.on_fail.emit(self.name, self.mac)


class GetContactInformationSignals(QtCore.QObject):
    """These are the signals emitted by the GetContactInformationThread"""
    on_error = QtCore.pyqtSignal(str, int)
    on_result = QtCore.pyqtSignal(dict)
    on_finished = QtCore.pyqtSignal()


class GetContactInformationThread(QtCore.QRunnable):
    """This thread gets contact information from another contact"""
    def __init__(self, ip, port=42000, timeout=3):
        super(GetContactInformationThread, self).__init__()
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.signals = GetContactInformationSignals()

    @QtCore.pyqtSlot()
    def run(self):
        """This is the method that is called when the thread starts"""
        try:
            result = asyncio.run(inbox.get_contact_information(self.ip, self.port, self.timeout))
        except Exception as e:
            self.signals.on_error.emit(self.ip, self.port)
        else:
            self.signals.on_result.emit(result)
        finally:
            self.signals.on_finished.emit()


class StartFtpClientConnectionSignals(QtCore.QObject):
    """These are the signals emitted by a StartFtpClientConnectionThread"""
    on_error = QtCore.pyqtSignal(str, int)
    on_result = QtCore.pyqtSignal('PyQt_PyObject')
    on_connect = QtCore.pyqtSignal(str)
    on_finished = QtCore.pyqtSignal()


class StartFtpClientConnectionThread(QtCore.QRunnable):
    """This thread starts an FTP connection with another contact"""
    def __init__(self, ip, port=42000, timeout=3):
        super(StartFtpClientConnectionThread, self).__init__()
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.signals = StartFtpClientConnectionSignals()

    def run(self):
        """This is the method that is called when the thread starts"""
        try:
            ftp = ftplib.FTP()
            banner = ftp.connect(host=self.ip, port=self.port, timeout=self.timeout)
            self.signals.on_connect.emit(banner)
            ftp.login(user='hotline', passwd='hotpassword')
        except Exception as e:
            self.signals.on_error.emit(self.ip, self.port)
        else:
            self.signals.on_result.emit(ftp)
        finally:
            self.signals.on_finished.emit()


class UploadFileSignals(QtCore.QObject):
    """These are the signals emitted by a UploadFileThread"""
    # host, port, filename  <<< When you should freeze actions
    on_start = QtCore.pyqtSignal(str, int, str)
    # host, port, filename, exception
    on_error = QtCore.pyqtSignal(str, int, str, 'PyQt_PyObject')
    # host, port, filename
    on_finished = QtCore.pyqtSignal(str, int, str)
    # When you should unfreeze actions
    on_end = QtCore.pyqtSignal()


class UploadFileThread(QtCore.QRunnable):
    """This thread uploads a file to a FTP server"""
    def __init__(self, filename, ftp_conn: ftplib.FTP):
        super(UploadFileThread, self).__init__()
        self.filename = filename
        self.ftp_conn = ftp_conn
        self.signals = UploadFileSignals()

    def run(self):
        """This method is called when the thread starts"""
        try:
            with open(self.filename, 'rb') as f:
                self.signals.on_start.emit(self.ftp_conn.host, self.ftp_conn.port, self.filename)
                self.ftp_conn.storbinary(f"STOR {os.path.split(self.filename)[1]}", f)
        except Exception as e:
            self.signals.on_error.emit(self.ftp_conn.host, self.ftp_conn.port, self.filename, e)
        else:
            self.signals.on_finished.emit(self.ftp_conn.host, self.ftp_conn.port, self.filename)
        finally:
            self.signals.on_end.emit()


class DownloadFileSignals(QtCore.QObject):
    """These are the signals emitted by a DownloadFileSignals"""
    # host, port, filename
    on_start = QtCore.pyqtSignal(str, int, str)
    # host, port, filename, exception
    on_error = QtCore.pyqtSignal(str, int, str, 'PyQt_PyObject')
    # host, port, filename
    on_finished = QtCore.pyqtSignal(str, int, str)
    on_end = QtCore.pyqtSignal()


class DownloadFileThread(QtCore.QRunnable):
    """This thread downloads a file from a FTP server"""
    def __init__(self, filename, ftp_conn: ftplib.FTP, folder_to_save):
        super(DownloadFileThread, self).__init__()
        self.filename = filename
        self.ftp_conn = ftp_conn
        self.folder_to_save = folder_to_save
        self.signals = DownloadFileSignals()

    def run(self) -> None:
        """This method is called when the thread starts"""
        try:
            self.signals.on_start.emit(self.ftp_conn.host, self.ftp_conn.port, self.filename)
            # self.filename = f"{self.ftp_conn.pwd()}/{self.filename}"
            filepath = os.path.join(self.folder_to_save, self.filename)
            with open(filepath, 'wb') as fp:
                self.ftp_conn.retrbinary(f'RETR {os.path.split(self.filename)[1]}', fp.write)
        except Exception as e:
            self.signals.on_error.emit(self.ftp_conn.host, self.ftp_conn.port, self.filename, e)
        else:
            self.signals.on_finished.emit(self.ftp_conn.host, self.ftp_conn.port, self.filename)
        finally:
            self.signals.on_end.emit()


class SignUpRequestSiganls(QtCore.QObject):
    """These are the signals emitted by a SignUpRequestThread"""
    on_start = QtCore.pyqtSignal()
    on_error = QtCore.pyqtSignal('PyQt_PyObject')
    on_result = QtCore.pyqtSignal(dict)


class SignUpRequestThread(QtCore.QRunnable):
    """This thread makes a SignUp request to an Interlocutor server"""
    def __init__(self, server_addr, server_port, server_password, c_mac, c_name, c_port, c_getonlybymac):
        super(SignUpRequestThread, self).__init__()
        self.server_address = server_addr
        self.server_port = server_port
        self.server_password = server_password
        self.signals = SignUpRequestSiganls()

        self.c_mac = c_mac
        self.c_name = c_name
        self.c_port = c_port
        self.c_getonlybymac = c_getonlybymac

    def run(self) -> None:
        """This method is called when the thread starts"""
        request = inter.sign_up(self.c_mac, self.c_name, self.c_port, self.c_getonlybymac)
        try:
            self.signals.on_start.emit()
            result = asyncio.run(request.send_to(self.server_address, self.server_port, password=self.server_password))
        except Exception as e:
            self.signals.on_error.emit(e)
        else:
            self.signals.on_result.emit(result)


class GetRequestSignals(QtCore.QObject):
    """These are the signals emitted by a GetRequestThread"""
    on_start = QtCore.pyqtSignal()
    on_result = QtCore.pyqtSignal(dict)
    on_error = QtCore.pyqtSignal('PyQt_PyObject')
    on_finished = QtCore.pyqtSignal()


class GetRequestThread(QtCore.QRunnable):
    """This thread makes a Get request to an Interlocutor server"""
    def __init__(self, server_addr, server_port, server_password, mac=None, username=None):
        super(GetRequestThread, self).__init__()
        self.server_address = server_addr
        self.server_port = server_port
        self.server_password = server_password
        self.signals = GetRequestSignals()
        if mac:
            self.request = inter.get_by_mac(mac)
        else:
            self.request = inter.get_by_username(username)

    def run(self) -> None:
        """This method is called when the thread starts"""
        try:
            self.signals.on_start.emit()
            result = asyncio.run(
                self.request.send_to(self.server_address, self.server_port, password=self.server_password))
        except Exception as e:
            self.signals.on_error.emit(e)
        else:
            self.signals.on_result.emit(result)
        finally:
            self.signals.on_finished.emit()


class DropRequestSignals(QtCore.QObject):
    """These are the signals emitted by a DropRequestThread"""
    on_start = QtCore.pyqtSignal(str)
    on_error = QtCore.pyqtSignal('PyQt_PyObject', str)
    on_result = QtCore.pyqtSignal(dict)
    on_finished = QtCore.pyqtSignal()


class DropRequestThread(QtCore.QRunnable):
    """This thread makes a Drop request to an Interlocutor server"""
    def __init__(self, server_address, server_port, server_password, ip_to_drop):
        super(DropRequestThread, self).__init__()
        self.signals = DropRequestSignals()
        self.server_address = server_address
        self.server_port = server_port
        self.server_password = server_password
        self.ip_to_drop = ip_to_drop

    def run(self) -> None:
        """This method is called when the thread starts"""
        try:
            request = inter.drop(self.ip_to_drop)
            self.signals.on_start.emit(self.ip_to_drop)
            result = asyncio.run(request.send_to(self.server_address, self.server_port, password=self.server_password))
        except Exception as e:
            self.signals.on_error.emit(e, self.ip_to_drop)
        else:
            self.signals.on_result.emit(result)
        finally:
            self.signals.on_finished.emit()
