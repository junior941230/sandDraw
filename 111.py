import numpy as np
import matplotlib.pyplot as plt


def plotSignals():
    # 建立畫布與兩個子圖
    figureObject, (axOne, axTwo) = plt.subplots(2, 1, figsize=(8, 10))

    # 繪製 P-18 的 y(t)
    timeArrayOne = np.linspace(-1, 9, 500)
    yValuesOne = np.piecewise(timeArrayOne,
                              [timeArrayOne < 1,
                               (timeArrayOne >= 1) & (timeArrayOne < 3),
                                  (timeArrayOne >= 3) & (timeArrayOne < 5),
                                  (timeArrayOne >= 5) & (timeArrayOne < 7),
                                  timeArrayOne >= 7],
                              [0,
                                  lambda t: -6*t + 6,
                                  -12,
                                  lambda t: 6*t - 42,
                                  0]
                              )

    axOne.plot(timeArrayOne, yValuesOne, 'b-', linewidth=2)
    axOne.set_title('P-18: Convolution Output y(t)')
    axOne.set_xlabel('t')
    axOne.set_ylabel('y(t)')
    axOne.grid(True)
    axOne.axhline(0, color='black', linewidth=1)
    axOne.axvline(0, color='black', linewidth=1)
    # 標示轉折點
    keyPointsXOne = [1, 3, 5, 7]
    keyPointsYOne = [0, -12, -12, 0]
    axOne.plot(keyPointsXOne, keyPointsYOne, 'ro')

    # 繪製 P-22(c) 的 y'(t)
    timeArrayTwo = np.array([-4, -3, -2, -1, 0, 1, 2, 3, 4])
    yValuesTwo = np.array([0, 0, -1, 0, 2, 0, -1, 0, 0])

    axTwo.plot(timeArrayTwo, yValuesTwo, 'r-', linewidth=2)
    axTwo.set_title("P-22(c): Derivative of Output y'(t)")
    axTwo.set_xlabel('t')
    axTwo.set_ylabel("y'(t)")
    axTwo.grid(True)
    axTwo.axhline(0, color='black', linewidth=1)
    axTwo.axvline(0, color='black', linewidth=1)
    # 標示轉折點
    axTwo.plot(timeArrayTwo[1:-1], yValuesTwo[1:-1], 'bo')

    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    plotSignals()
