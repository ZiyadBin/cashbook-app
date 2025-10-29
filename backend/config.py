{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": 1,
   "id": "97f38c18",
   "metadata": {},
   "outputs": [],
   "source": [
    "import os\n",
    "from datetime import timedelta\n",
    "\n",
    "class Config:\n",
    "    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-here')\n",
    "    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-dev-secret-here')\n",
    "    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)\n",
    "    JWT_TOKEN_LOCATION = ['headers']"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "2d0308d2",
   "metadata": {},
   "outputs": [],
   "source": []
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3 (ipykernel)",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.9.13"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
