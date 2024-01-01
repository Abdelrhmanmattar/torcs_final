class PI_CONTROLLER:
    #CREATE PI CONTROLLER
    def __init__(self, kp, ki,kd, refrance):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.refrance = refrance
        self.int = 0
        self.prev_error = 0

    def set_refrance(self, refrance):
        self.refrance = refrance
    #UPDATE PI CONTROLLER
    def output(self , current_int , prev_time , current_time):
        error = self.refrance - current_int #ERROR
        Pcontroler = self.kp * error #P CONTROLLER
        if error == 0:
            self.int = 0
        dt = current_time - prev_time
        integral = self.int + error * dt

        if integral > 1:
            integral = 1
        elif integral < -1:
            integral = -1
        Icontroler = self.ki * integral #I CONTROLLER

        self.int = integral

        #Dcontroler = self.kd * (error - self.prev_error) / dt #D CONTROLLER
        if dt != 0:
            derivative = (error - self.prev_error) / dt
            if derivative > 1:
                derivative = 1
            elif derivative < -1:
                derivative = -1
            Dcontroler = self.kd * derivative
            
        else:
            Dcontroler = 0

        self.prev_error = error
        return (Pcontroler + Icontroler + Dcontroler)
    
    def reset(self):
        self.int = 0
        self.prev_error = 0
if __name__ == "__main__":
    print(22%1)